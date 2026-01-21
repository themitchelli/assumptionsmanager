<script lang="ts">
	import {
		Grid,
		Row,
		Column,
		Tile,
		ClickableTile,
		SkeletonText
	} from 'carbon-components-svelte';
	import TableSplit from 'carbon-icons-svelte/lib/TableSplit.svelte';
	import Upload from 'carbon-icons-svelte/lib/Upload.svelte';
	import { auth, isAdmin } from '$lib/stores/auth';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { onMount } from 'svelte';
	import PendingApprovalsCard from '$lib/components/PendingApprovalsCard.svelte';
	import { api } from '$lib/api';
	import type { DashboardStatsResponse } from '$lib/api/types';

	let stats: DashboardStatsResponse | null = null;
	let loading = true;
	let error: string | null = null;

	async function loadStats() {
		loading = true;
		error = null;

		const response = await api.get<DashboardStatsResponse>('/dashboard/stats');

		if (response.error) {
			error = response.error.message;
			stats = null;
		} else if (response.data) {
			stats = response.data;
		}

		loading = false;
	}

	onMount(() => {
		breadcrumbs.set([{ label: 'Dashboard' }]);
		loadStats();
	});
</script>

<svelte:head>
	<title>Dashboard - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">
				Welcome{$auth.user?.name ? `, ${$auth.user.name}` : ''}
			</h1>
			{#if $auth.user}
				<p class="tenant-context">
					Tenant: {$auth.user.tenant_name || 'Unnamed Tenant'}
				</p>
			{/if}
		</Column>
	</Row>

	<Row class="stats-row">
		<Column sm={4} md={4} lg={4}>
			<Tile class="stat-tile">
				<span class="stat-title">Tables</span>
				{#if loading}
					<SkeletonText class="stat-skeleton" />
				{:else}
					<span class="stat-value">{error ? '--' : stats?.table_count ?? 0}</span>
				{/if}
				<span class="stat-description">Assumption tables in your tenant</span>
			</Tile>
		</Column>
		<Column sm={4} md={4} lg={4}>
			<Tile class="stat-tile">
				<span class="stat-title">Recent Activity</span>
				{#if loading}
					<SkeletonText class="stat-skeleton" />
				{:else}
					<span class="stat-value">{error ? '--' : stats?.recent_activity_count ?? 0}</span>
				{/if}
				<span class="stat-description">Updates in the last 7 days</span>
			</Tile>
		</Column>
		<Column sm={4} md={4} lg={4}>
			<Tile class="stat-tile">
				<span class="stat-title">Versions</span>
				{#if loading}
					<SkeletonText class="stat-skeleton" />
				{:else}
					<span class="stat-value">{error ? '--' : stats?.version_count ?? 0}</span>
				{/if}
				<span class="stat-description">Total version snapshots</span>
			</Tile>
		</Column>
	</Row>

	{#if $isAdmin}
		<Row>
			<Column sm={4} md={8} lg={8}>
				<PendingApprovalsCard />
			</Column>
		</Row>
	{/if}

	<Row>
		<Column>
			<h2 class="section-title">Quick Actions</h2>
		</Column>
	</Row>

	<Row>
		<Column sm={4} md={4} lg={4}>
			<ClickableTile href="/tables" class="action-tile">
				<TableSplit size={32} />
				<h3>View Tables</h3>
				<p>Browse and manage assumption tables</p>
			</ClickableTile>
		</Column>
		<Column sm={4} md={4} lg={4}>
			<ClickableTile href="/tables/import" class="action-tile">
				<Upload size={32} />
				<h3>Import CSV</h3>
				<p>Upload a CSV file to create or update tables</p>
			</ClickableTile>
		</Column>
	</Row>
</Grid>

<style>
	.page-title {
		margin-bottom: 0.5rem;
		font-size: 2rem;
		font-weight: 400;
	}

	.tenant-context {
		color: var(--cds-text-secondary);
		margin-bottom: 2rem;
	}

	.section-title {
		margin-top: 2rem;
		margin-bottom: 1rem;
		font-size: 1.25rem;
		font-weight: 600;
	}

	:global(.stats-row) {
		margin-bottom: 1rem;
	}

	:global(.stat-tile) {
		min-height: 150px;
		display: flex;
		flex-direction: column;
	}

	:global(.stat-tile .stat-title) {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin-bottom: 0.5rem;
	}

	:global(.stat-tile .stat-value) {
		font-size: 2.5rem;
		font-weight: 300;
		margin-bottom: 0.5rem;
	}

	:global(.stat-tile .stat-skeleton) {
		height: 2.5rem;
		width: 3rem;
		margin-bottom: 0.5rem;
	}

	:global(.stat-tile .stat-description) {
		font-size: 0.875rem;
		color: var(--cds-text-helper);
	}

	:global(.action-tile) {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-height: 150px;
	}

	:global(.action-tile h3) {
		font-size: 1rem;
		font-weight: 600;
		margin-top: 0.5rem;
	}

	:global(.action-tile p) {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
	}
</style>
