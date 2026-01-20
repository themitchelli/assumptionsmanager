<script lang="ts">
	import { Grid, Row, Column, Tile } from 'carbon-components-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		breadcrumbs.set([{ label: 'Admin', href: '/admin/users' }, { label: 'Tenants' }]);
	});
</script>

<svelte:head>
	<title>Tenants - Admin - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Tenant Management</h1>
		</Column>
	</Row>
	<Row>
		<Column>
			<Tile>
				<p>Tenant management will be implemented in PRD-016.</p>
			</Tile>
		</Column>
	</Row>
</Grid>

<style>
	.page-title {
		margin-bottom: 1.5rem;
		font-size: 2rem;
		font-weight: 400;
	}
</style>
