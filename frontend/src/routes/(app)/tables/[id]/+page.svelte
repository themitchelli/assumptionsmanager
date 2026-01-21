<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		Tile,
		Tag,
		Button,
		SkeletonText,
		SkeletonPlaceholder,
		ToastNotification
	} from 'carbon-components-svelte';
	import { ArrowLeft, Calendar, Time, Add } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { toasts } from '$lib/stores/toast';
	import { api } from '$lib/api';
	import type { TableDetailResponse, ColumnResponse } from '$lib/api/types';
	import AddColumnModal from '$lib/components/AddColumnModal.svelte';

	// Get table ID from route
	$: tableId = $page.params.id;

	// State
	let table: TableDetailResponse | null = null;
	let loading = true;
	let error: string | null = null;

	// Modal state
	let showAddColumnModal = false;

	// Role-based permissions
	$: canEdit = $auth.user?.role === 'analyst' || $auth.user?.role === 'admin' || $auth.user?.role === 'super_admin';

	// Get existing column names for validation
	$: existingColumnNames = table?.columns.map((c) => c.name) || [];

	// Fetch table data
	async function fetchTable() {
		loading = true;
		error = null;
		const response = await api.get<TableDetailResponse>(`/tables/${tableId}`);
		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			table = response.data;
			// Update breadcrumbs with actual table name
			breadcrumbs.set([
				{ label: 'Tables', href: '/tables' },
				{ label: table.name }
			]);
		}
		loading = false;
	}

	// Format date for display
	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	// Format datetime for display
	function formatDateTime(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Get data type tag color
	function getDataTypeTag(dataType: string): { text: string; type: 'blue' | 'green' | 'purple' | 'cyan' | 'teal' } {
		switch (dataType) {
			case 'integer':
				return { text: 'INT', type: 'blue' };
			case 'decimal':
				return { text: 'DEC', type: 'cyan' };
			case 'date':
				return { text: 'DATE', type: 'purple' };
			case 'boolean':
				return { text: 'BOOL', type: 'teal' };
			case 'text':
			default:
				return { text: 'TEXT', type: 'green' };
		}
	}

	// Format cell value based on data type
	function formatCellValue(value: string | number | boolean | null | undefined, dataType: string): string {
		if (value === null || value === undefined) {
			return '';
		}

		switch (dataType) {
			case 'boolean':
				return value ? 'Yes' : 'No';
			case 'date':
				// Dates are stored as strings, display as-is
				return String(value);
			case 'decimal':
				// Format decimals with appropriate precision
				if (typeof value === 'number') {
					return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 });
				}
				return String(value);
			case 'integer':
				if (typeof value === 'number') {
					return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
				}
				return String(value);
			case 'text':
			default:
				return String(value);
		}
	}

	// Sort columns by position
	$: sortedColumns = table?.columns.slice().sort((a, b) => a.position - b.position) || [];

	// Back to tables list
	function handleBack() {
		goto('/tables');
	}

	// Handle column created
	function handleColumnCreated(event: CustomEvent<ColumnResponse>) {
		const newColumn = event.detail;
		if (table) {
			// Add new column to table
			table = {
				...table,
				columns: [...table.columns, newColumn]
			};
		}
		showAddColumnModal = false;
		toasts.success('Column added', `Column "${newColumn.name}" has been added to the table`);
	}

	onMount(() => {
		// Set initial breadcrumbs (will update when data loads)
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: 'Loading...' }
		]);
		fetchTable();
	});
</script>

<svelte:head>
	<title>{table?.name || 'Table Detail'} - Assumptions Manager</title>
</svelte:head>

<Grid>
	<!-- Back button and header -->
	<Row>
		<Column>
			<Button
				kind="ghost"
				icon={ArrowLeft}
				on:click={handleBack}
				class="back-button"
			>
				Back to Tables
			</Button>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error loading table"
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
			<Column lg={4} md={4} sm={4}>
				<SkeletonPlaceholder style="height: 80px; width: 100%;" />
			</Column>
			<Column lg={4} md={4} sm={4}>
				<SkeletonPlaceholder style="height: 80px; width: 100%;" />
			</Column>
			<Column lg={4} md={4} sm={4}>
				<SkeletonPlaceholder style="height: 80px; width: 100%;" />
			</Column>
		</Row>
		<Row>
			<Column>
				<div class="grid-skeleton">
					<SkeletonPlaceholder style="height: 400px; width: 100%;" />
				</div>
			</Column>
		</Row>
	{:else if table}
		<!-- Table header with metadata -->
		<Row>
			<Column>
				<div class="table-header">
					<div class="table-header-top">
						<h1 class="table-name">{table.name}</h1>
						{#if canEdit}
							<Button
								kind="primary"
								icon={Add}
								on:click={() => (showAddColumnModal = true)}
							>
								Add Column
							</Button>
						{/if}
					</div>
					{#if table.description}
						<p class="table-description">{table.description}</p>
					{/if}
				</div>
			</Column>
		</Row>

		<!-- Metadata tiles -->
		<Row class="metadata-row">
			<Column lg={4} md={4} sm={4}>
				<Tile class="metadata-tile">
					<div class="metadata-label">
						<Calendar size={16} />
						<span>Created</span>
					</div>
					<div class="metadata-value">{formatDateTime(table.created_at)}</div>
				</Tile>
			</Column>
			<Column lg={4} md={4} sm={4}>
				<Tile class="metadata-tile">
					<div class="metadata-label">
						<Time size={16} />
						<span>Last Modified</span>
					</div>
					<div class="metadata-value">{formatDateTime(table.updated_at || table.created_at)}</div>
				</Tile>
			</Column>
			{#if table.effective_date}
				<Column lg={4} md={4} sm={4}>
					<Tile class="metadata-tile">
						<div class="metadata-label">
							<Calendar size={16} />
							<span>Effective Date</span>
						</div>
						<div class="metadata-value">{formatDate(table.effective_date)}</div>
					</Tile>
				</Column>
			{/if}
		</Row>

		<!-- Data grid -->
		<Row>
			<Column>
				<div class="data-grid-container">
					{#if sortedColumns.length === 0}
						<!-- No columns yet -->
						<div class="empty-state">
							<h3>No columns defined</h3>
							<p>This table doesn't have any columns yet. Add columns to start entering data.</p>
							{#if canEdit}
								<Button
									kind="primary"
									icon={Add}
									on:click={() => (showAddColumnModal = true)}
									class="empty-state-button"
								>
									Add Column
								</Button>
							{/if}
						</div>
					{:else if table.rows.length === 0}
						<!-- Columns but no rows -->
						<div class="data-grid-wrapper">
							<table class="data-grid">
								<thead>
									<tr>
										<th class="row-index-header">#</th>
										{#each sortedColumns as column}
											<th class="column-header">
												<div class="column-header-content">
													<span class="column-name">{column.name}</span>
													<Tag type={getDataTypeTag(column.data_type).type} size="sm">
														{getDataTypeTag(column.data_type).text}
													</Tag>
												</div>
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									<tr>
										<td colspan={sortedColumns.length + 1} class="empty-rows">
											<p>No data rows. Add rows to enter data.</p>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					{:else}
						<!-- Full data grid -->
						<div class="data-grid-wrapper">
							<table class="data-grid">
								<thead>
									<tr>
										<th class="row-index-header">#</th>
										{#each sortedColumns as column}
											<th class="column-header">
												<div class="column-header-content">
													<span class="column-name">{column.name}</span>
													<Tag type={getDataTypeTag(column.data_type).type} size="sm">
														{getDataTypeTag(column.data_type).text}
													</Tag>
												</div>
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each table.rows as row}
										<tr>
											<td class="row-index-cell">{row.row_index}</td>
											{#each sortedColumns as column}
												{@const cellValue = row.cells[column.name]}
												{@const formattedValue = formatCellValue(cellValue, column.data_type)}
												<td
													class="data-cell"
													class:empty-cell={cellValue === null || cellValue === undefined || cellValue === ''}
													class:boolean-cell={column.data_type === 'boolean'}
													class:number-cell={column.data_type === 'integer' || column.data_type === 'decimal'}
												>
													{#if cellValue === null || cellValue === undefined || cellValue === ''}
														<span class="empty-placeholder">—</span>
													{:else}
														{formattedValue}
													{/if}
												</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			</Column>
		</Row>

		<!-- Summary info -->
		<Row>
			<Column>
				<div class="summary-info">
					<span>{sortedColumns.length} column{sortedColumns.length !== 1 ? 's' : ''}</span>
					<span class="separator">•</span>
					<span>{table.rows.length} row{table.rows.length !== 1 ? 's' : ''}</span>
				</div>
			</Column>
		</Row>
	{/if}
</Grid>

<!-- Add Column Modal -->
<AddColumnModal
	bind:open={showAddColumnModal}
	tableId={tableId}
	existingColumnNames={existingColumnNames}
	on:close={() => (showAddColumnModal = false)}
	on:created={handleColumnCreated}
/>

<style>
	:global(.back-button) {
		margin-bottom: 1rem;
	}

	.header-skeleton {
		margin-bottom: 1.5rem;
	}

	.grid-skeleton {
		margin-top: 1.5rem;
	}

	.table-header {
		margin-bottom: 1.5rem;
	}

	.table-header-top {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.table-name {
		font-size: 2rem;
		font-weight: 400;
		margin-bottom: 0.5rem;
	}

	.table-description {
		color: var(--cds-text-secondary, #525252);
		font-size: 1rem;
	}

	:global(.metadata-row) {
		margin-bottom: 1.5rem;
	}

	:global(.metadata-tile) {
		height: 100%;
	}

	.metadata-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--cds-text-secondary, #525252);
		font-size: 0.875rem;
		margin-bottom: 0.25rem;
	}

	.metadata-value {
		font-size: 1rem;
		font-weight: 500;
	}

	.data-grid-container {
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
		padding: 1rem;
	}

	.data-grid-wrapper {
		overflow-x: auto;
		overflow-y: auto;
		max-height: 600px;
		border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
		border-radius: 4px;
		background: var(--cds-layer-02, #ffffff);
	}

	.data-grid {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	.data-grid thead {
		position: sticky;
		top: 0;
		z-index: 1;
	}

	.row-index-header,
	.column-header {
		background: var(--cds-layer-accent-01, #e0e0e0);
		padding: 0.75rem 1rem;
		text-align: left;
		font-weight: 600;
		border-bottom: 2px solid var(--cds-border-strong-01, #8d8d8d);
		white-space: nowrap;
	}

	.row-index-header {
		width: 60px;
		min-width: 60px;
		text-align: center;
		color: var(--cds-text-secondary, #525252);
	}

	.column-header-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.column-name {
		font-weight: 600;
	}

	.row-index-cell,
	.data-cell {
		padding: 0.5rem 1rem;
		border-bottom: 1px solid var(--cds-border-subtle-01, #e0e0e0);
		vertical-align: middle;
	}

	.row-index-cell {
		background: var(--cds-layer-01, #f4f4f4);
		text-align: center;
		color: var(--cds-text-secondary, #525252);
		font-weight: 500;
		width: 60px;
		min-width: 60px;
	}

	.data-cell {
		min-width: 120px;
		max-width: 300px;
	}

	.number-cell {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.boolean-cell {
		text-align: center;
	}

	.empty-cell {
		background: var(--cds-layer-01, #f4f4f4);
	}

	.empty-placeholder {
		color: var(--cds-text-disabled, #c6c6c6);
	}

	.data-grid tbody tr:hover {
		background: var(--cds-layer-hover-01, #e8e8e8);
	}

	.data-grid tbody tr:nth-child(even) {
		background: var(--cds-layer-01, #f4f4f4);
	}

	.data-grid tbody tr:nth-child(even):hover {
		background: var(--cds-layer-hover-01, #e8e8e8);
	}

	.empty-rows {
		text-align: center;
		padding: 2rem 1rem;
		color: var(--cds-text-secondary, #525252);
	}

	.empty-state {
		text-align: center;
		padding: 3rem 1rem;
	}

	.empty-state h3 {
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

	.empty-state p {
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 1rem;
	}

	:global(.empty-state-button) {
		margin-top: 0.5rem;
	}

	.summary-info {
		margin-top: 1rem;
		color: var(--cds-text-secondary, #525252);
		font-size: 0.875rem;
	}

	.separator {
		margin: 0 0.5rem;
	}
</style>
