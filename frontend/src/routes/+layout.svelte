<script lang="ts">
	import 'carbon-components-svelte/css/g10.css';
	import { navigating } from '$app/stores';
	import { isNavigating } from '$lib/stores/navigation';

	// Update navigation loading state when route transitions happen
	$: isNavigating.set($navigating !== null);
</script>

<svelte:head>
	<link rel="icon" href="/favicon.svg" />
	<title>Assumptions Manager</title>
</svelte:head>

<slot />
