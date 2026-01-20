<script lang="ts">
	import { Grid, Row, Column, Tile, ClickableTile } from 'carbon-components-svelte';
	import TableSplit from 'carbon-icons-svelte/lib/TableSplit.svelte';
	import Upload from 'carbon-icons-svelte/lib/Upload.svelte';
	import { auth } from '$lib/stores/auth';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		breadcrumbs.set([{ label: 'Dashboard' }]);
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
			{#if $auth.user?.tenant_name || $auth.user?.tenant_id}
				<p class="tenant-context">
					Tenant: {$auth.user.tenant_name || $auth.user.tenant_id}
				</p>
			{/if}
		</Column>
	</Row>

	<Row>
		<Column sm={4} md={4} lg={4}>
			<Tile class="stat-tile">
				<h3 class="stat-title">Tables</h3>
				<p class="stat-value">--</p>
				<p class="stat-description">Assumption tables in your tenant</p>
			</Tile>
		</Column>
		<Column sm={4} md={4} lg={4}>
			<Tile class="stat-tile">
				<h3 class="stat-title">Pending Approvals</h3>
				<p class="stat-value">--</p>
				<p class="stat-description">Versions awaiting review</p>
			</Tile>
		</Column>
		<Column sm={4} md={4} lg={4}>
			<Tile class="stat-tile">
				<h3 class="stat-title">Recent Activity</h3>
				<p class="stat-value">--</p>
				<p class="stat-description">Updates in the last 7 days</p>
			</Tile>
		</Column>
	</Row>

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
			<ClickableTile href="/tables?import=true" class="action-tile">
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

	:global(.stat-tile) {
		min-height: 150px;
	}

	:global(.stat-title) {
		font-size: 0.875rem;
		color: var(--cds-text-secondary);
		margin-bottom: 0.5rem;
	}

	:global(.stat-value) {
		font-size: 2.5rem;
		font-weight: 300;
		margin-bottom: 0.5rem;
	}

	:global(.stat-description) {
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
