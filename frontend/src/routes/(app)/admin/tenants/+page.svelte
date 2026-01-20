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
		Tag,
		Button,
		SkeletonText,
		ToastNotification,
		Tile
	} from 'carbon-components-svelte';
	import { Add, UserMultiple, Enterprise, Checkmark } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { api } from '$lib/api';
	import type { TenantListItem, TenantListResponse, PlatformStatsResponse } from '$lib/api/types';

	// State
	let tenants: TenantListItem[] = [];
	let stats: PlatformStatsResponse | null = null;
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

	// Computed filtered and sorted data
	$: filteredTenants = tenants.filter((tenant) => {
		if (searchQuery === '') return true;
		return tenant.name.toLowerCase().includes(searchQuery.toLowerCase());
	});

	$: sortedTenants = [...filteredTenants].sort((a, b) => {
		if (sortDirection === 'none') return 0;
		const modifier = sortDirection === 'ascending' ? 1 : -1;
		const aVal = getSortValue(a, sortKey);
		const bVal = getSortValue(b, sortKey);
		if (aVal < bVal) return -1 * modifier;
		if (aVal > bVal) return 1 * modifier;
		return 0;
	});

	$: paginatedTenants = sortedTenants.slice((page - 1) * pageSize, page * pageSize);

	$: totalItems = filteredTenants.length;

	function getSortValue(tenant: TenantListItem, key: string): string | number {
		switch (key) {
			case 'name':
				return tenant.name.toLowerCase();
			case 'user_count':
				return tenant.user_count;
			case 'status':
				return tenant.status;
			case 'created_at':
				return new Date(tenant.created_at).getTime();
			default:
				return '';
		}
	}

	// DataTable headers
	const headers = [
		{ key: 'name', value: 'Tenant Name' },
		{ key: 'user_count', value: 'Users' },
		{ key: 'status', value: 'Status' },
		{ key: 'created_at', value: 'Created' },
		{ key: 'actions', value: 'Actions', sort: false as const }
	];

	// Formatted rows for DataTable
	$: rows = paginatedTenants.map((tenant) => ({
		id: tenant.id,
		name: tenant.name,
		user_count: tenant.user_count,
		status: tenant.status,
		statusDisplay: getStatusDisplay(tenant.status),
		created_at: formatDate(tenant.created_at)
	}));

	function getStatusDisplay(status: string): { text: string; type: 'green' | 'gray' } {
		switch (status) {
			case 'active':
				return { text: 'Active', type: 'green' };
			case 'inactive':
				return { text: 'Inactive', type: 'gray' };
			default:
				return { text: 'Unknown', type: 'gray' };
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	function handleSort(
		event: CustomEvent<{
			header: { key: string };
			sortDirection?: 'ascending' | 'descending' | 'none';
		}>
	) {
		sortKey = event.detail.header.key;
		sortDirection = event.detail.sortDirection || 'none';
	}

	function handleRowClick(tenantId: string) {
		// Navigate to tenant detail view
		goto(`/admin/tenants/${tenantId}`);
	}

	async function fetchData() {
		loading = true;
		error = null;

		// Fetch tenants and stats in parallel
		const [tenantsResponse, statsResponse] = await Promise.all([
			api.get<TenantListResponse>('/tenants'),
			api.get<PlatformStatsResponse>('/tenants/stats')
		]);

		if (tenantsResponse.error) {
			error = tenantsResponse.error.message;
		} else if (tenantsResponse.data) {
			tenants = tenantsResponse.data.tenants;
		}

		if (statsResponse.data) {
			stats = statsResponse.data;
		}

		loading = false;
	}

	onMount(() => {
		breadcrumbs.set([{ label: 'Admin', href: '/admin/users' }, { label: 'All Tenants' }]);
		fetchData();
	});
</script>

<svelte:head>
	<title>All Tenants - Admin - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Platform Administration</h1>
			<p class="page-description">Manage all tenants across the platform</p>
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

	<!-- Stats Tiles -->
	<Row class="stats-row">
		<Column sm={4} md={2} lg={4}>
			<Tile class="stat-tile">
				<div class="stat-icon">
					<Enterprise size={24} />
				</div>
				<div class="stat-content">
					<span class="stat-value">{stats?.total_tenants ?? '-'}</span>
					<span class="stat-label">Total Tenants</span>
				</div>
			</Tile>
		</Column>
		<Column sm={4} md={2} lg={4}>
			<Tile class="stat-tile">
				<div class="stat-icon stat-icon--green">
					<Checkmark size={24} />
				</div>
				<div class="stat-content">
					<span class="stat-value">{stats?.active_tenants ?? '-'}</span>
					<span class="stat-label">Active Tenants</span>
				</div>
			</Tile>
		</Column>
		<Column sm={4} md={2} lg={4}>
			<Tile class="stat-tile">
				<div class="stat-icon stat-icon--blue">
					<UserMultiple size={24} />
				</div>
				<div class="stat-content">
					<span class="stat-value">{stats?.total_users ?? '-'}</span>
					<span class="stat-label">Total Users</span>
				</div>
			</Tile>
		</Column>
	</Row>

	<Row>
		<Column>
			{#if loading}
				<div class="skeleton-container">
					<SkeletonText heading />
					<SkeletonText paragraph lines={5} />
				</div>
			{:else if tenants.length === 0}
				<div class="empty-state">
					<h3>No tenants found</h3>
					<p>Create your first tenant to get started.</p>
					<Button icon={Add}>Create Tenant</Button>
				</div>
			{:else}
				<DataTable {headers} {rows} sortable on:click:header={handleSort} size="medium">
					<Toolbar>
						<ToolbarContent>
							<ToolbarSearch
								bind:value={searchQuery}
								placeholder="Search tenants..."
								persistent
							/>
							<Button icon={Add}>Create Tenant</Button>
						</ToolbarContent>
					</Toolbar>
					<svelte:fragment slot="cell" let:row let:cell>
						{#if cell.key === 'name'}
							<button class="row-link" on:click={() => handleRowClick(row.id)}>
								{cell.value}
							</button>
						{:else if cell.key === 'status'}
							<Tag type={row.statusDisplay.type}>{row.statusDisplay.text}</Tag>
						{:else if cell.key === 'actions'}
							<Button
								kind="ghost"
								size="small"
								on:click={() => handleRowClick(row.id)}
							>
								View
							</Button>
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

	:global(.stats-row) {
		margin-bottom: 1.5rem;
	}

	:global(.stat-tile) {
		display: flex;
		align-items: center;
		gap: 1rem;
		padding: 1rem;
	}

	.stat-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 48px;
		height: 48px;
		border-radius: 8px;
		background: var(--cds-layer-02, #e0e0e0);
		color: var(--cds-text-secondary, #525252);
	}

	.stat-icon--green {
		background: #defbe6;
		color: #198038;
	}

	.stat-icon--blue {
		background: #d0e2ff;
		color: #0043ce;
	}

	.stat-content {
		display: flex;
		flex-direction: column;
	}

	.stat-value {
		font-size: 1.5rem;
		font-weight: 600;
		line-height: 1.2;
	}

	.stat-label {
		font-size: 0.875rem;
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

	.row-link {
		background: none;
		border: none;
		padding: 0;
		color: var(--cds-link-01, #0f62fe);
		cursor: pointer;
		text-decoration: none;
		font-size: inherit;
		font-family: inherit;
	}

	.row-link:hover {
		text-decoration: underline;
	}

	:global(.bx--data-table) {
		margin-bottom: 1rem;
	}

	:global(.bx--toolbar-content) {
		gap: 0.5rem;
	}
</style>
