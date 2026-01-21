<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		DataTable,
		Toolbar,
		ToolbarContent,
		Button,
		SkeletonText,
		Tag,
		ToastNotification,
		Tooltip
	} from 'carbon-components-svelte';
	import { ArrowLeft, Add, Compare, Time, User } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { toasts } from '$lib/stores/toast';
	import { api } from '$lib/api';
	import type { VersionListResponse, TableListResponse } from '$lib/api/types';

	// Get table ID from route
	$: tableId = $page.params.id;

	// State
	let versions: VersionListResponse[] = [];
	let tableName = '';
	let loading = true;
	let error: string | null = null;

	// Expandable row state
	let expandedRowIds: Set<string> = new Set();
	let versionDetails: Map<string, { cell_count: number; loading: boolean }> = new Map();

	// Role-based permissions
	$: canCreateVersion =
		$auth.user?.role === 'analyst' ||
		$auth.user?.role === 'admin' ||
		$auth.user?.role === 'super_admin';

	// Selection state for comparison
	let selectedVersionIds: string[] = [];
	$: canCompare = selectedVersionIds.length === 2;

	// DataTable headers
	const headers = [
		{ key: 'version_number', value: 'Version' },
		{ key: 'comment', value: 'Comment' },
		{ key: 'created_by_name', value: 'Created By' },
		{ key: 'created_at', value: 'Created At' },
		{ key: 'approval_status', value: 'Status' }
	];

	// Format relative time
	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'Just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;

		return date.toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	// Format absolute datetime for tooltip
	function formatAbsoluteTime(dateStr: string): string {
		return new Date(dateStr).toLocaleString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Get approval status tag type
	function getStatusTag(
		status: string | undefined
	): { type: 'blue' | 'green' | 'red' | 'gray' | 'purple'; text: string } {
		switch (status) {
			case 'approved':
				return { type: 'green', text: 'Approved' };
			case 'submitted':
				return { type: 'blue', text: 'Submitted' };
			case 'rejected':
				return { type: 'red', text: 'Rejected' };
			case 'draft':
			default:
				return { type: 'gray', text: 'Draft' };
		}
	}

	// Fetch versions
	async function fetchVersions() {
		loading = true;
		error = null;

		// Fetch table info first to get the name
		const tableResponse = await api.get<TableListResponse[]>('/tables');
		if (tableResponse.data) {
			const table = tableResponse.data.find((t) => t.id === tableId);
			if (table) {
				tableName = table.name;
			}
		}

		// Fetch versions
		const response = await api.get<VersionListResponse[]>(`/tables/${tableId}/versions`);
		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			versions = response.data;
		}

		// Update breadcrumbs
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: tableName || 'Table', href: `/tables/${tableId}` },
			{ label: 'Versions' }
		]);

		loading = false;
	}

	// Handle row expansion
	async function handleRowExpand(rowId: string) {
		if (expandedRowIds.has(rowId)) {
			expandedRowIds.delete(rowId);
			expandedRowIds = expandedRowIds;
		} else {
			expandedRowIds.add(rowId);
			expandedRowIds = expandedRowIds;

			// Fetch version details if not already loaded
			if (!versionDetails.has(rowId)) {
				versionDetails.set(rowId, { cell_count: 0, loading: true });
				versionDetails = versionDetails;

				const response = await api.get<{ rows: { cells: Record<string, unknown> }[] }>(
					`/tables/${tableId}/versions/${rowId}`
				);

				if (response.data) {
					// Count cells
					let cellCount = 0;
					for (const row of response.data.rows) {
						cellCount += Object.keys(row.cells).length;
					}
					versionDetails.set(rowId, { cell_count: cellCount, loading: false });
				} else {
					versionDetails.set(rowId, { cell_count: 0, loading: false });
				}
				versionDetails = versionDetails;
			}
		}
	}

	// Reactively enforce selection limit
	$: if (selectedVersionIds.length > 2) {
		// Keep only the last 2 selected
		selectedVersionIds = selectedVersionIds.slice(-2);
		toasts.info('Selection limit', 'You can only select 2 versions to compare');
	}

	// Handle compare button click
	function handleCompare() {
		if (selectedVersionIds.length !== 2) return;

		// Order versions: older first (v1), newer second (v2)
		const selectedVersions = versions.filter((v) => selectedVersionIds.includes(v.id));
		selectedVersions.sort((a, b) => a.version_number - b.version_number);

		const v1 = selectedVersions[0].id;
		const v2 = selectedVersions[1].id;

		goto(`/tables/${tableId}/versions/compare?v1=${v1}&v2=${v2}`);
	}

	// Navigate back to table detail
	function handleBack() {
		goto(`/tables/${tableId}`);
	}

	// Navigate to create snapshot (placeholder for US-002)
	function handleCreateSnapshot() {
		// Will be implemented in US-002
		toasts.info('Coming soon', 'Create snapshot functionality will be available soon');
	}

	onMount(() => {
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: 'Loading...', href: `/tables/${tableId}` },
			{ label: 'Versions' }
		]);
		fetchVersions();
	});
</script>

<svelte:head>
	<title>Version History - {tableName || 'Table'} - Assumptions Manager</title>
</svelte:head>

<Grid>
	<!-- Back button -->
	<Row>
		<Column>
			<Button kind="ghost" icon={ArrowLeft} on:click={handleBack} class="back-button">
				Back to Table
			</Button>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error loading versions"
					subtitle={error}
					lowContrast
					on:close={() => (error = null)}
				/>
			</Column>
		</Row>
	{/if}

	{#if loading}
		<!-- Loading skeleton -->
		<Row>
			<Column>
				<div class="header-skeleton">
					<SkeletonText heading width="40%" />
					<SkeletonText width="60%" />
				</div>
			</Column>
		</Row>
		<Row>
			<Column>
				<SkeletonText paragraph lines={5} />
			</Column>
		</Row>
	{:else}
		<!-- Page header -->
		<Row>
			<Column>
				<div class="page-header">
					<h1>Version History</h1>
					<p class="subtitle">{tableName}</p>
				</div>
			</Column>
		</Row>

		{#if versions.length === 0}
			<!-- Empty state -->
			<Row>
				<Column>
					<div class="empty-state">
						<Time size={32} />
						<h3>No versions yet</h3>
						<p>Create a snapshot to start tracking changes to this table.</p>
						{#if canCreateVersion}
							<Button kind="primary" icon={Add} on:click={handleCreateSnapshot}>
								Create First Snapshot
							</Button>
						{:else}
							<p class="viewer-note">Only analysts and admins can create snapshots.</p>
						{/if}
					</div>
				</Column>
			</Row>
		{:else}
			<!-- Version table -->
			<Row>
				<Column>
					<DataTable
						headers={headers}
						rows={versions.map((v) => ({
							id: v.id,
							version_number: v.version_number,
							comment: v.comment,
							created_by_name: v.created_by_name || 'Unknown',
							created_at: v.created_at,
							approval_status: v.approval_status
						}))}
						sortable
						selectable
						bind:selectedRowIds={selectedVersionIds}
						on:click:row={(e) => handleRowExpand(e.detail.id)}
						expandable
						expandedRowIds={Array.from(expandedRowIds)}
					>
						<Toolbar>
							<ToolbarContent>
								<div class="toolbar-info">
									{#if selectedVersionIds.length === 0}
										<span class="hint">Select 2 versions to compare</span>
									{:else if selectedVersionIds.length === 1}
										<span class="hint">Select 1 more version to compare</span>
									{:else if selectedVersionIds.length === 2}
										<span class="ready">Ready to compare</span>
									{/if}
								</div>
								<Button
									kind="secondary"
									icon={Compare}
									disabled={!canCompare}
									on:click={handleCompare}
								>
									Compare Selected
								</Button>
								{#if canCreateVersion}
									<Button kind="primary" icon={Add} on:click={handleCreateSnapshot}>
										Create Snapshot
									</Button>
								{/if}
							</ToolbarContent>
						</Toolbar>

						<svelte:fragment slot="cell" let:cell>
							{#if cell.key === 'version_number'}
								<span class="version-number">v{cell.value}</span>
							{:else if cell.key === 'comment'}
								<span class="comment" title={cell.value}>
									{cell.value.length > 60 ? cell.value.slice(0, 60) + '...' : cell.value}
								</span>
							{:else if cell.key === 'created_by_name'}
								<span class="created-by">
									<User size={16} />
									{cell.value}
								</span>
							{:else if cell.key === 'created_at'}
								<Tooltip triggerText={formatRelativeTime(cell.value)} direction="top">
									{formatAbsoluteTime(cell.value)}
								</Tooltip>
							{:else if cell.key === 'approval_status'}
								{@const tag = getStatusTag(cell.value)}
								<Tag type={tag.type} size="sm">{tag.text}</Tag>
							{:else}
								{cell.value}
							{/if}
						</svelte:fragment>

						<svelte:fragment slot="expanded-row" let:row>
							<div class="expanded-content">
								{#if versionDetails.get(row.id)?.loading}
									<SkeletonText width="200px" />
								{:else}
									<div class="detail-row">
										<strong>Full comment:</strong>
										<span>{versions.find((v) => v.id === row.id)?.comment || ''}</span>
									</div>
									<div class="detail-row">
										<strong>Cell count:</strong>
										<span>{versionDetails.get(row.id)?.cell_count || 0} cells</span>
									</div>
									<div class="detail-row">
										<strong>Created:</strong>
										<span
											>{formatAbsoluteTime(
												versions.find((v) => v.id === row.id)?.created_at || ''
											)}</span
										>
									</div>
								{/if}
							</div>
						</svelte:fragment>
					</DataTable>
				</Column>
			</Row>

			<!-- Compare footer -->
			{#if selectedVersionIds.length === 2}
				<Row>
					<Column>
						<div class="compare-footer">
							<Button kind="primary" icon={Compare} on:click={handleCompare}>
								Compare Selected Versions
							</Button>
						</div>
					</Column>
				</Row>
			{/if}
		{/if}
	{/if}
</Grid>

<style>
	:global(.back-button) {
		margin-bottom: 1rem;
	}

	.header-skeleton {
		margin-bottom: 1.5rem;
	}

	.page-header {
		margin-bottom: 1.5rem;
	}

	.page-header h1 {
		font-size: 2rem;
		font-weight: 400;
		margin-bottom: 0.25rem;
	}

	.subtitle {
		color: var(--cds-text-secondary, #525252);
		font-size: 1rem;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4rem 2rem;
		text-align: center;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.empty-state :global(svg) {
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 1rem;
	}

	.empty-state h3 {
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

	.empty-state p {
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 1.5rem;
	}

	.viewer-note {
		font-size: 0.875rem;
		font-style: italic;
	}

	.toolbar-info {
		flex: 1;
		display: flex;
		align-items: center;
	}

	.hint {
		color: var(--cds-text-secondary, #525252);
		font-size: 0.875rem;
	}

	.ready {
		color: var(--cds-support-success, #24a148);
		font-size: 0.875rem;
		font-weight: 500;
	}

	.version-number {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.comment {
		color: var(--cds-text-primary, #161616);
	}

	.created-by {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.created-by :global(svg) {
		color: var(--cds-text-secondary, #525252);
	}

	.expanded-content {
		padding: 1rem 2rem;
		background: var(--cds-layer-01, #f4f4f4);
	}

	.detail-row {
		margin-bottom: 0.5rem;
	}

	.detail-row strong {
		margin-right: 0.5rem;
	}

	.compare-footer {
		display: flex;
		justify-content: center;
		padding: 1.5rem;
		margin-top: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}
</style>
