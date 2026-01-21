<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		Button,
		SkeletonText,
		Tag,
		ToastNotification,
		Accordion,
		AccordionItem,
		Tile,
		InlineNotification
	} from 'carbon-components-svelte';
	import {
		ArrowLeft,
		ArrowRight,
		Add,
		Subtract,
		Edit,
		User,
		Calendar
	} from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { api } from '$lib/api';
	import type { FormattedDiffResponse, TableListResponse } from '$lib/api/types';

	// Get route params
	$: tableId = $page.params.id;
	$: v1 = $page.url.searchParams.get('v1');
	$: v2 = $page.url.searchParams.get('v2');

	// State
	let diff: FormattedDiffResponse | null = null;
	let tableName = '';
	let loading = true;
	let error: string | null = null;

	// Format dates
	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Calculate percentage for visual bars
	function calculatePercentage(value: number, total: number): number {
		if (total === 0) return 0;
		return Math.min(100, Math.round((value / total) * 100));
	}

	// Get change type icon and color
	function getChangeTypeStyle(column: {
		has_additions: boolean;
		has_removals: boolean;
		has_modifications: boolean;
	}): { icon: typeof Add; color: string; label: string }[] {
		const types: { icon: typeof Add; color: string; label: string }[] = [];
		if (column.has_additions) types.push({ icon: Add, color: 'green', label: 'Additions' });
		if (column.has_removals) types.push({ icon: Subtract, color: 'red', label: 'Removals' });
		if (column.has_modifications) types.push({ icon: Edit, color: 'purple', label: 'Modifications' });
		return types;
	}

	// Fetch diff data
	async function fetchDiff() {
		if (!v1 || !v2) {
			error = 'Missing version parameters. Please select two versions to compare.';
			loading = false;
			return;
		}

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

		// Fetch diff
		const response = await api.get<FormattedDiffResponse>(
			`/tables/${tableId}/versions/diff?v1=${v1}&v2=${v2}`
		);

		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			diff = response.data;
		}

		// Update breadcrumbs
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: tableName || 'Table', href: `/tables/${tableId}` },
			{ label: 'Versions', href: `/tables/${tableId}/versions` },
			{ label: 'Compare' }
		]);

		loading = false;
	}

	// Navigate back
	function handleBack() {
		goto(`/tables/${tableId}/versions`);
	}

	onMount(() => {
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: 'Loading...', href: `/tables/${tableId}` },
			{ label: 'Versions', href: `/tables/${tableId}/versions` },
			{ label: 'Compare' }
		]);
		fetchDiff();
	});
</script>

<svelte:head>
	<title>Compare Versions - {tableName || 'Table'} - Assumptions Manager</title>
</svelte:head>

<Grid>
	<!-- Back button -->
	<Row>
		<Column>
			<Button kind="ghost" icon={ArrowLeft} on:click={handleBack} class="back-button">
				Back to Versions
			</Button>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error loading diff"
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
					<SkeletonText heading width="60%" />
					<SkeletonText width="40%" />
				</div>
			</Column>
		</Row>
		<Row>
			<Column lg={4} md={4} sm={4}>
				<SkeletonText paragraph lines={4} />
			</Column>
			<Column lg={4} md={4} sm={4}>
				<SkeletonText paragraph lines={4} />
			</Column>
			<Column lg={4} md={4} sm={4}>
				<SkeletonText paragraph lines={4} />
			</Column>
		</Row>
	{:else if diff}
		<!-- Page header with version comparison -->
		<Row>
			<Column>
				<div class="page-header">
					<h1>Comparing Versions</h1>
					<p class="subtitle">{tableName}</p>
				</div>
			</Column>
		</Row>

		<!-- Version comparison header -->
		<Row>
			<Column>
				<div class="version-comparison-header">
					<div class="version-box version-a">
						<Tag type="outline">Baseline</Tag>
						<span class="version-number">v{diff.version_a.version_number}</span>
						<div class="version-meta">
							<span class="meta-item">
								<Calendar size={16} />
								{formatDate(diff.version_a.created_at)}
							</span>
							<span class="meta-item">
								<User size={16} />
								{diff.version_a.created_by_name || 'Unknown'}
							</span>
						</div>
						{#if diff.version_a.comment}
							<p class="version-comment">{diff.version_a.comment}</p>
						{/if}
					</div>

					<div class="arrow-container">
						<ArrowRight size={32} />
					</div>

					<div class="version-box version-b">
						<Tag type="blue">Comparison</Tag>
						<span class="version-number">v{diff.version_b.version_number}</span>
						<div class="version-meta">
							<span class="meta-item">
								<Calendar size={16} />
								{formatDate(diff.version_b.created_at)}
							</span>
							<span class="meta-item">
								<User size={16} />
								{diff.version_b.created_by_name || 'Unknown'}
							</span>
						</div>
						{#if diff.version_b.comment}
							<p class="version-comment">{diff.version_b.comment}</p>
						{/if}
					</div>
				</div>
			</Column>
		</Row>

		<!-- Summary stats panel -->
		<Row>
			<Column>
				<Tile class="summary-tile">
					<h3 class="summary-title">Change Summary</h3>

					{#if diff.summary.total_changes === 0}
						<InlineNotification
							kind="info"
							title="No changes"
							subtitle="These versions are identical."
							hideCloseButton
							lowContrast
						/>
					{:else}
						<div class="stats-grid">
							<!-- Total changes -->
							<div class="stat-card">
								<span class="stat-value">{diff.summary.total_changes}</span>
								<span class="stat-label">Total Changes</span>
							</div>

							<!-- Rows added -->
							<div class="stat-card stat-added">
								<div class="stat-header">
									<Add size={20} />
									<span class="stat-value">{diff.summary.rows_added}</span>
								</div>
								<span class="stat-label">Rows Added</span>
								<div class="stat-bar">
									<div
										class="stat-bar-fill added"
										style="width: {calculatePercentage(diff.summary.rows_added, diff.summary.total_changes)}%"
									></div>
								</div>
							</div>

							<!-- Rows removed -->
							<div class="stat-card stat-removed">
								<div class="stat-header">
									<Subtract size={20} />
									<span class="stat-value">{diff.summary.rows_removed}</span>
								</div>
								<span class="stat-label">Rows Removed</span>
								<div class="stat-bar">
									<div
										class="stat-bar-fill removed"
										style="width: {calculatePercentage(diff.summary.rows_removed, diff.summary.total_changes)}%"
									></div>
								</div>
							</div>

							<!-- Cells modified -->
							<div class="stat-card stat-modified">
								<div class="stat-header">
									<Edit size={20} />
									<span class="stat-value">{diff.summary.cells_modified}</span>
								</div>
								<span class="stat-label">Cells Modified</span>
								<div class="stat-bar">
									<div
										class="stat-bar-fill modified"
										style="width: {calculatePercentage(diff.summary.cells_modified, diff.summary.total_changes)}%"
									></div>
								</div>
							</div>
						</div>
					{/if}
				</Tile>
			</Column>
		</Row>

		<!-- Column-level summary accordion -->
		{#if diff.column_summary && diff.column_summary.length > 0}
			<Row>
				<Column>
					<h3 class="section-title">Changes by Column</h3>
					<Accordion>
						{#each diff.column_summary as column}
							{@const hasChanges = column.change_count > 0}
							{@const changeTypes = getChangeTypeStyle(column)}
							<AccordionItem
								title={column.column_name}
								open={hasChanges}
							>
								<svelte:fragment slot="title">
									<div class="accordion-title">
										<span class="column-name">{column.column_name}</span>
										{#if hasChanges}
											<Tag type="high-contrast" size="sm">{column.change_count} change{column.change_count !== 1 ? 's' : ''}</Tag>
										{:else}
											<Tag type="gray" size="sm">No changes</Tag>
										{/if}
									</div>
								</svelte:fragment>

								<div class="column-detail">
									{#if hasChanges}
										<div class="change-types">
											{#each changeTypes as changeType}
												<span class="change-type change-type-{changeType.color}">
													<svelte:component this={changeType.icon} size={16} />
													{changeType.label}
												</span>
											{/each}
										</div>
										<p class="change-description">
											This column has {column.change_count} cell{column.change_count !== 1 ? 's' : ''} affected by changes.
											{#if column.has_additions && column.has_removals && column.has_modifications}
												Includes additions, removals, and modifications.
											{:else if column.has_additions && column.has_removals}
												Includes additions and removals.
											{:else if column.has_additions && column.has_modifications}
												Includes additions and modifications.
											{:else if column.has_removals && column.has_modifications}
												Includes removals and modifications.
											{:else if column.has_additions}
												All changes are additions.
											{:else if column.has_removals}
												All changes are removals.
											{:else if column.has_modifications}
												All changes are modifications to existing values.
											{/if}
										</p>
									{:else}
										<p class="no-changes-message">No changes detected in this column.</p>
									{/if}
								</div>
							</AccordionItem>
						{/each}
					</Accordion>
				</Column>
			</Row>
		{/if}

		<!-- Placeholder for cell-level diff (US-005) -->
		{#if diff.summary.total_changes > 0}
			<Row>
				<Column>
					<div class="cell-diff-placeholder">
						<p>Cell-level diff view will be implemented in the next story.</p>
						<p class="change-count">{diff.changes.length} row{diff.changes.length !== 1 ? 's' : ''} with changes</p>
					</div>
				</Column>
			</Row>
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
		margin-bottom: 1rem;
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

	/* Version comparison header */
	.version-comparison-header {
		display: flex;
		align-items: stretch;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.version-box {
		flex: 1;
		padding: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
		border-left: 4px solid var(--cds-border-subtle-01, #e0e0e0);
	}

	.version-a {
		border-left-color: var(--cds-text-secondary, #525252);
	}

	.version-b {
		border-left-color: var(--cds-link-primary, #0f62fe);
	}

	.version-number {
		display: block;
		font-size: 1.5rem;
		font-weight: 600;
		margin: 0.5rem 0;
		font-variant-numeric: tabular-nums;
	}

	.version-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		margin-bottom: 0.5rem;
	}

	.meta-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
	}

	.meta-item :global(svg) {
		color: var(--cds-icon-secondary, #525252);
	}

	.version-comment {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
		font-style: italic;
		margin-top: 0.5rem;
		max-height: 3em;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.arrow-container {
		display: flex;
		align-items: center;
		color: var(--cds-text-secondary, #525252);
	}

	/* Summary tile */
	:global(.summary-tile) {
		margin-bottom: 1.5rem;
	}

	.summary-title {
		font-size: 1.125rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
		gap: 1rem;
	}

	.stat-card {
		padding: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.stat-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.stat-value {
		font-size: 2rem;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.stat-label {
		display: block;
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
		margin-top: 0.25rem;
	}

	.stat-bar {
		height: 4px;
		background: var(--cds-border-subtle-01, #e0e0e0);
		border-radius: 2px;
		margin-top: 0.75rem;
		overflow: hidden;
	}

	.stat-bar-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.3s ease;
	}

	.stat-bar-fill.added {
		background: var(--cds-support-success, #24a148);
	}

	.stat-bar-fill.removed {
		background: var(--cds-support-error, #da1e28);
	}

	.stat-bar-fill.modified {
		background: var(--cds-support-warning, #f1c21b);
	}

	.stat-added .stat-header {
		color: var(--cds-support-success, #24a148);
	}

	.stat-removed .stat-header {
		color: var(--cds-support-error, #da1e28);
	}

	.stat-modified .stat-header {
		color: var(--cds-support-warning, #f1c21b);
	}

	/* Section title */
	.section-title {
		font-size: 1.125rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	/* Accordion styling */
	.accordion-title {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		width: 100%;
	}

	.column-name {
		font-weight: 500;
	}

	.column-detail {
		padding: 0.5rem 0;
	}

	.change-types {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.change-type {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.875rem;
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	.change-type-green {
		color: var(--cds-support-success, #24a148);
		background: rgba(36, 161, 72, 0.1);
	}

	.change-type-red {
		color: var(--cds-support-error, #da1e28);
		background: rgba(218, 30, 40, 0.1);
	}

	.change-type-purple {
		color: var(--cds-support-info, #0043ce);
		background: rgba(0, 67, 206, 0.1);
	}

	.change-description {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
	}

	.no-changes-message {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
		font-style: italic;
	}

	/* Cell diff placeholder */
	.cell-diff-placeholder {
		padding: 2rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
		text-align: center;
		margin-top: 1rem;
	}

	.cell-diff-placeholder p {
		color: var(--cds-text-secondary, #525252);
		margin: 0;
	}

	.cell-diff-placeholder .change-count {
		font-weight: 500;
		margin-top: 0.5rem;
	}

	/* Responsive */
	@media (max-width: 672px) {
		.version-comparison-header {
			flex-direction: column;
		}

		.arrow-container {
			transform: rotate(90deg);
			justify-content: center;
			padding: 0.5rem 0;
		}

		.stats-grid {
			grid-template-columns: 1fr 1fr;
		}
	}
</style>
