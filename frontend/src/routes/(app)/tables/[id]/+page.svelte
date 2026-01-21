<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { Grid, Row, Column, Tile, SkeletonText } from 'carbon-components-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';

	$: tableId = $page.params.id;

	onMount(() => {
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: 'Table Detail' }
		]);
	});
</script>

<svelte:head>
	<title>Table Detail - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Table Detail</h1>
		</Column>
	</Row>
	<Row>
		<Column>
			<Tile>
				<p>Table ID: {tableId}</p>
				<p>Full table detail view will be implemented in US-003.</p>
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
