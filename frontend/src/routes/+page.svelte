<script lang="ts">
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';
	import { auth } from '$lib/stores/auth';

	// Wait for auth check to complete, then redirect appropriately
	$: if (browser && !$auth.isLoading) {
		if ($auth.isAuthenticated) {
			goto('/dashboard');
		} else {
			goto('/login');
		}
	}
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
