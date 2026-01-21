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
		Tooltip,
		Dropdown
	} from 'carbon-components-svelte';
	import { ArrowLeft, Add, Compare, Time, User, ChevronRight, Restart } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { toasts } from '$lib/stores/toast';
	import { api } from '$lib/api';
	import type { VersionListResponse, TableListResponse, TableDetailResponse } from '$lib/api/types';
	import CreateSnapshotModal from '$lib/components/CreateSnapshotModal.svelte';
	import RestoreVersionModal from '$lib/components/RestoreVersionModal.svelte';

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

	// Restore is admin-only per acceptance criteria
	$: canRestore =
		$auth.user?.role === 'admin' ||
		$auth.user?.role === 'super_admin';

	// Selection state for comparison
	let selectedVersionIds: string[] = [];
	$: canCompare = selectedVersionIds.length === 2;

	// Modal state
	let showCreateModal = false;
	let showRestoreModal = false;
	let restoreVersion: VersionListResponse | null = null;

	// Status filter state
	let statusFilter: string = 'all';
	const statusFilterItems = [
		{ id: 'all', text: 'All' },
		{ id: 'draft', text: 'Draft' },
		{ id: 'submitted', text: 'Submitted' },
		{ id: 'approved', text: 'Approved' },
		{ id: 'rejected', text: 'Rejected' }
	];

	// DataTable headers
	const headers = [
		{ key: 'version_number', value: 'Version' },
		{ key: 'comment', value: 'Comment' },
		{ key: 'created_by_name', value: 'Created By' },
		{ key: 'created_at', value: 'Created At' },
		{ key: 'approval_status', value: 'Status' },
		{ key: 'actions', value: 'Actions', empty: true }
	];

	// Get previous version for comparison
	function getPreviousVersion(currentVersion: VersionListResponse): VersionListResponse | null {
		const sortedVersions = [...versions].sort((a, b) => b.version_number - a.version_number);
		const currentIndex = sortedVersions.findIndex((v) => v.id === currentVersion.id);
		if (currentIndex >= 0 && currentIndex < sortedVersions.length - 1) {
			return sortedVersions[currentIndex + 1];
		}
		return null;
	}

	// Quick compare with previous version
	function handleCompareWithPrevious(version: VersionListResponse) {
		const previousVersion = getPreviousVersion(version);
		if (!previousVersion) return;

		// Order: older version as v1, newer as v2
		goto(`/tables/${tableId}/versions/compare?v1=${previousVersion.id}&v2=${version.id}`);
	}

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

	// Build status tooltip text
	function getStatusTooltip(version: VersionListResponse): string | null {
		const status = version.approval_status;
		if (status === 'draft' || !status) {
			return null; // No tooltip for draft
		}

		const parts: string[] = [];

		if (status === 'submitted' && version.submitted_by_name && version.submitted_at) {
			parts.push(`Submitted by ${version.submitted_by_name}`);
			parts.push(formatAbsoluteTime(version.submitted_at));
		} else if (status === 'approved' && version.reviewed_by_name && version.reviewed_at) {
			parts.push(`Approved by ${version.reviewed_by_name}`);
			parts.push(formatAbsoluteTime(version.reviewed_at));
		} else if (status === 'rejected' && version.reviewed_by_name && version.reviewed_at) {
			parts.push(`Rejected by ${version.reviewed_by_name}`);
			parts.push(formatAbsoluteTime(version.reviewed_at));
		}

		return parts.length > 0 ? parts.join('\n') : null;
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

		// Build URL with status filter
		let url = `/tables/${tableId}/versions`;
		if (statusFilter && statusFilter !== 'all') {
			url += `?status=${statusFilter}`;
		}

		// Fetch versions
		const response = await api.get<VersionListResponse[]>(url);
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

	// Handle status filter change
	function handleStatusFilterChange(event: CustomEvent<{ selectedId: string }>) {
		statusFilter = event.detail.selectedId;
		fetchVersions();
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

	// Open create snapshot modal
	function handleCreateSnapshot() {
		showCreateModal = true;
	}

	// Handle snapshot created
	function handleSnapshotCreated(event: CustomEvent<VersionListResponse>) {
		const newVersion = event.detail;
		toasts.success('Snapshot created', `Version ${newVersion.version_number} has been created`);
		showCreateModal = false;
		// Refresh the version list
		fetchVersions();
	}

	// Handle modal close
	function handleModalClose() {
		showCreateModal = false;
	}

	// Open restore modal
	function handleRestore(version: VersionListResponse) {
		restoreVersion = version;
		showRestoreModal = true;
	}

	// Handle version restored
	function handleVersionRestored(_event: CustomEvent<TableDetailResponse>) {
		toasts.success('Version restored', `Table has been restored to v${restoreVersion?.version_number}. A new snapshot has been created for audit trail.`);
		showRestoreModal = false;
		restoreVersion = null;
		// Navigate to table detail to see the restored data
		goto(`/tables/${tableId}`);
	}

	// Handle restore modal close
	function handleRestoreModalClose() {
		showRestoreModal = false;
		restoreVersion = null;
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
								<div class="toolbar-filter">
									<Dropdown
										titleText=""
										hideLabel
										size="sm"
										selectedId={statusFilter}
										items={statusFilterItems}
										on:select={handleStatusFilterChange}
									/>
								</div>
								<div class="toolbar-info">
									{#if selectedVersionIds.length === 0}
										<span class="hint">Select 2 versions to compare</span>
									{:else if selectedVersionIds.length === 1}
										<span class="hint">Select 1 more version to compare</span>
									{:else if selectedVersionIds.length === 2}
										<span class="ready">Ready to compare</span>
									{/if}
								</div>
								{#if canCompare}
								<Button
									kind="secondary"
									icon={Compare}
									on:click={handleCompare}
								>
									Compare Selected
								</Button>
							{:else}
								<div
									class="compare-tooltip-wrapper"
									title={selectedVersionIds.length === 0
										? 'Select 2 versions to compare'
										: selectedVersionIds.length === 1
											? 'Select 1 more version'
											: 'Select exactly 2 versions'}
								>
									<Button
										kind="secondary"
										icon={Compare}
										disabled
									>
										Compare Selected
									</Button>
								</div>
							{/if}
								{#if canCreateVersion}
									<Button kind="primary" icon={Add} on:click={handleCreateSnapshot}>
										Create Snapshot
									</Button>
								{:else}
									<div title="Only analysts and admins can create snapshots">
										<Button kind="primary" icon={Add} disabled>
											Create Snapshot
										</Button>
									</div>
								{/if}
							</ToolbarContent>
						</Toolbar>

						<svelte:fragment slot="cell" let:cell let:row>
							{#if cell.key === 'version_number'}
								<span class="version-number">v{cell.value}</span>
							{:else if cell.key === 'comment'}
								<span class="comment" title={cell.value}>
									{cell.value && cell.value.length > 60
										? cell.value.slice(0, 60) + '...'
										: cell.value || ''}
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
								{@const version = versions.find((v) => v.id === row.id)}
								{@const tag = getStatusTag(cell.value)}
								{@const tooltip = version ? getStatusTooltip(version) : null}
								{#if tooltip}
									<Tooltip direction="top">
										<span slot="triggerText">
											<Tag type={tag.type} size="sm">{tag.text}</Tag>
										</span>
										<div class="status-tooltip">
											{#each tooltip.split('\n') as line}
												<div>{line}</div>
											{/each}
										</div>
									</Tooltip>
								{:else}
									<Tag type={tag.type} size="sm">{tag.text}</Tag>
								{/if}
							{:else if cell.key === 'actions'}
								{@const version = versions.find((v) => v.id === row.id)}
								{@const hasPrevious = version ? getPreviousVersion(version) !== null : false}
								<div class="actions-cell">
									{#if hasPrevious}
										<Button
											kind="ghost"
											size="small"
											icon={ChevronRight}
											iconDescription="Compare with previous version"
											on:click={(e) => {
												e.stopPropagation();
												if (version) handleCompareWithPrevious(version);
											}}
										>
											Compare with previous
										</Button>
									{:else}
										<span class="no-previous">First version</span>
									{/if}
									{#if canRestore && version}
										<Button
											kind="ghost"
											size="small"
											icon={Restart}
											iconDescription="Restore this version"
											on:click={(e) => {
												e.stopPropagation();
												handleRestore(version);
											}}
										>
											Restore
										</Button>
									{/if}
								</div>
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

<!-- Create Snapshot Modal -->
<CreateSnapshotModal
	bind:open={showCreateModal}
	{tableId}
	on:created={handleSnapshotCreated}
	on:close={handleModalClose}
/>

<!-- Restore Version Modal -->
{#if restoreVersion}
	<RestoreVersionModal
		bind:open={showRestoreModal}
		{tableId}
		{tableName}
		versionId={restoreVersion.id}
		versionNumber={restoreVersion.version_number}
		approvalStatus={restoreVersion.approval_status}
		on:restored={handleVersionRestored}
		on:close={handleRestoreModalClose}
	/>
{/if}

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

	.compare-tooltip-wrapper {
		display: inline-block;
	}

	.no-previous {
		color: var(--cds-text-secondary, #525252);
		font-size: 0.875rem;
		font-style: italic;
	}

	.actions-cell {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.toolbar-filter {
		margin-right: 1rem;
	}

	.toolbar-filter :global(.bx--dropdown) {
		min-width: 140px;
	}

	.status-tooltip {
		text-align: left;
	}

	.status-tooltip div {
		white-space: nowrap;
	}
</style>
