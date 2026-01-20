<script lang="ts">
	import 'carbon-components-svelte/css/g10.css';
	import { onMount } from 'svelte';
	import { navigating } from '$app/stores';
	import { isNavigating } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';

	// Update navigation loading state when route transitions happen
	$: isNavigating.set($navigating !== null);

	// Initialize auth state from sessionStorage on app startup
	onMount(() => {
		auth.initialize();
	});
</script>

<svelte:head>
	<link rel="icon" href="/favicon.svg" />
	<title>Assumptions Manager</title>
</svelte:head>

<slot />
