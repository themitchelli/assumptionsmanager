<script lang="ts">
	import { Grid, Row, Column, Tile } from 'carbon-components-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		breadcrumbs.set([{ label: 'Admin', href: '/admin/users' }, { label: 'Users' }]);
	});
</script>

<svelte:head>
	<title>Users - Admin - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">User Management</h1>
		</Column>
	</Row>
	<Row>
		<Column>
			<Tile>
				<p>User management will be implemented in PRD-016.</p>
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
