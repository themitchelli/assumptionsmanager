<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	onMount(() => {
		// Redirect to dashboard (will be protected by route guards in US-006)
		goto('/dashboard');
	});
</script>

<div class="loading">
	<p>Redirecting...</p>
</div>

<style>
	.loading {
		display: flex;
		justify-content: center;
		align-items: center;
		height: 100vh;
	}
</style>
