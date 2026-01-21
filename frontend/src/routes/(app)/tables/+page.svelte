<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		DataTable,
		Toolbar,
		ToolbarContent,
		ToolbarSearch,
		Pagination,
		Button,
		SkeletonText,
		ToastNotification
	} from 'carbon-components-svelte';
	import { Add, View } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { api } from '$lib/api';
	import { toasts } from '$lib/stores/toast';
	import type { TableListResponse, TableResponse } from '$lib/api/types';
	import CreateTableModal from '$lib/components/CreateTableModal.svelte';

	// State
	let tables: TableListResponse[] = [];
	let loading = true;
	let error: string | null = null;

	// Filtering
	let searchQuery = '';

	// Pagination
	let page = 1;
	let pageSize = 10;
	const pageSizes = [10, 25, 50];

	// Sorting
	let sortKey: string = 'created_at';
	let sortDirection: 'ascending' | 'descending' | 'none' = 'descending';

	// Permission check
	$: canCreate = $auth.user?.role === 'analyst' || $auth.user?.role === 'admin' || $auth.user?.role === 'super_admin';

	// Computed filtered and sorted data
	$: filteredTables = tables.filter((table) => {
		if (searchQuery === '') return true;
		const query = searchQuery.toLowerCase();
		return (
			table.name.toLowerCase().includes(query) ||
			(table.description && table.description.toLowerCase().includes(query))
		);
	});

	$: sortedTables = [...filteredTables].sort((a, b) => {
		if (sortDirection === 'none') return 0;
		const modifier = sortDirection === 'ascending' ? 1 : -1;
		const aVal = getSortValue(a, sortKey);
		const bVal = getSortValue(b, sortKey);
		if (aVal < bVal) return -1 * modifier;
		if (aVal > bVal) return 1 * modifier;
		return 0;
	});

	$: paginatedTables = sortedTables.slice((page - 1) * pageSize, page * pageSize);

	$: totalItems = filteredTables.length;

	function getSortValue(table: TableListResponse, key: string): string | number {
		switch (key) {
			case 'name':
				return table.name.toLowerCase();
			case 'description':
				return (table.description || '').toLowerCase();
			case 'column_count':
				return table.column_count;
			case 'row_count':
				return table.row_count;
			case 'updated_at':
				return table.updated_at ? new Date(table.updated_at).getTime() : new Date(table.created_at).getTime();
			case 'created_at':
				return new Date(table.created_at).getTime();
			default:
				return '';
		}
	}

	// DataTable headers
	const headers = [
		{ key: 'name', value: 'Name' },
		{ key: 'description', value: 'Description' },
		{ key: 'column_count', value: 'Columns' },
		{ key: 'row_count', value: 'Rows' },
		{ key: 'updated_at', value: 'Last Modified' },
		{ key: 'actions', value: 'Actions', sort: false as const }
	];

	// Formatted rows for DataTable
	$: rows = paginatedTables.map((table) => ({
		id: table.id,
		name: table.name,
		description: table.description || '-',
		column_count: table.column_count,
		row_count: table.row_count,
		updated_at: formatDate(table.updated_at || table.created_at)
	}));

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function handleSort(event: CustomEvent<{ header: { key: string }; sortDirection?: 'ascending' | 'descending' | 'none' }>) {
		sortKey = event.detail.header.key;
		sortDirection = event.detail.sortDirection || 'none';
	}

	// Modal state
	let createModalOpen = false;

	// Existing table names for uniqueness validation
	$: existingTableNames = tables.map((t) => t.name);

	function handleRowClick(tableId: string) {
		goto(`/tables/${tableId}`);
	}

	function handleCreateTable() {
		createModalOpen = true;
	}

	function handleCreateModalClose() {
		createModalOpen = false;
	}

	function handleTableCreated(event: CustomEvent<TableResponse>) {
		createModalOpen = false;
		toasts.success('Table created', `"${event.detail.name}" has been created successfully.`);
		goto(`/tables/${event.detail.id}`);
	}

	async function fetchTables() {
		loading = true;
		error = null;
		const response = await api.get<TableListResponse[]>('/tables');
		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			tables = response.data;
		}
		loading = false;
	}

	onMount(() => {
		breadcrumbs.set([{ label: 'Tables' }]);
		fetchTables();
	});
</script>

<svelte:head>
	<title>Tables - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Assumption Tables</h1>
			<p class="page-description">View and manage your assumption tables</p>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error"
					subtitle={error}
					lowContrast
					on:close={() => (error = null)}
				/>
			</Column>
		</Row>
	{/if}

	<Row>
		<Column>
			{#if loading}
				<div class="skeleton-container">
					<SkeletonText heading />
					<SkeletonText paragraph lines={5} />
				</div>
			{:else if tables.length === 0}
				<div class="empty-state">
					<h3>No tables found</h3>
					<p>You haven't created any assumption tables yet.</p>
					{#if canCreate}
						<Button icon={Add} on:click={handleCreateTable}>Create Table</Button>
					{/if}
				</div>
			{:else}
				<DataTable
					{headers}
					{rows}
					sortable
					on:click:header={handleSort}
					size="medium"
				>
					<Toolbar>
						<ToolbarContent>
							<ToolbarSearch
								bind:value={searchQuery}
								placeholder="Search by name or description..."
								persistent
							/>
							{#if canCreate}
								<Button icon={Add} on:click={handleCreateTable}>Create Table</Button>
							{/if}
						</ToolbarContent>
					</Toolbar>
					<svelte:fragment slot="cell" let:row let:cell>
						{#if cell.key === 'name'}
							<button class="table-name-link" on:click={() => handleRowClick(row.id)}>
								{cell.value}
							</button>
						{:else if cell.key === 'actions'}
							<div class="action-buttons">
								<Button
									kind="ghost"
									size="small"
									icon={View}
									iconDescription="View table"
									on:click={() => handleRowClick(row.id)}
								/>
							</div>
						{:else}
							{cell.value}
						{/if}
					</svelte:fragment>
				</DataTable>

				<Pagination
					bind:pageSize
					bind:page
					{totalItems}
					{pageSizes}
					on:update={(e) => {
						page = e.detail.page;
						pageSize = e.detail.pageSize;
					}}
				/>
			{/if}
		</Column>
	</Row>
</Grid>

<CreateTableModal
	bind:open={createModalOpen}
	{existingTableNames}
	on:close={handleCreateModalClose}
	on:created={handleTableCreated}
/>

<style>
	.page-title {
		margin-bottom: 0.5rem;
		font-size: 2rem;
		font-weight: 400;
	}

	.page-description {
		margin-bottom: 1.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	.skeleton-container {
		padding: 1rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.empty-state h3 {
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

	.empty-state p {
		margin-bottom: 1.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	.table-name-link {
		background: none;
		border: none;
		color: var(--cds-link-01, #0f62fe);
		cursor: pointer;
		font-size: inherit;
		padding: 0;
		text-decoration: none;
	}

	.table-name-link:hover {
		text-decoration: underline;
	}

	.action-buttons {
		display: flex;
		gap: 0.25rem;
	}

	:global(.bx--data-table) {
		margin-bottom: 1rem;
	}

	:global(.bx--toolbar-content) {
		gap: 0.5rem;
	}
</style>
