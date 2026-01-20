<script lang="ts">
	import { Grid, Row, Column, Tile } from 'carbon-components-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		breadcrumbs.set([{ label: 'Tables' }]);
	});
</script>

<svelte:head>
	<title>Tables - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Assumption Tables</h1>
		</Column>
	</Row>
	<Row>
		<Column>
			<Tile>
				<p>Tables list will be implemented in PRD-017.</p>
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
