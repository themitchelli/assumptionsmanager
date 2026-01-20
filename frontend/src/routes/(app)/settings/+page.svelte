<script lang="ts">
	import { Grid, Row, Column, Tile } from 'carbon-components-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { onMount } from 'svelte';

	onMount(() => {
		breadcrumbs.set([{ label: 'Settings' }]);
	});
</script>

<svelte:head>
	<title>Settings - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Settings</h1>
		</Column>
	</Row>
	<Row>
		<Column>
			<Tile>
				<p>User settings will be implemented in a future release.</p>
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
