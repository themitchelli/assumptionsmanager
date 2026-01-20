<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { SkeletonPlaceholder } from 'carbon-components-svelte';
	import AppShell from '$lib/components/AppShell.svelte';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import { auth, isAdmin, isSuperAdmin } from '$lib/stores/auth';
	import { toasts } from '$lib/stores/toast';

	// Track if we've completed the auth check
	let authChecked = false;
	let authorized = false;

	// Define which routes require admin/super_admin roles
	// Note: /admin/tenant (singular) is for tenant settings (admin access)
	// /admin/tenants (plural) is for all tenants list (super_admin only)
	const adminRoutes = ['/admin/users', '/admin/tenant'];
	const superAdminRoutes = ['/admin/tenants'];  // Also protects /admin/tenants/[id] via startsWith

	$: currentPath = $page.url.pathname;

	// Check authentication and authorization
	$: if (browser && !$auth.isLoading) {
		if (!$auth.isAuthenticated) {
			// Not authenticated - redirect to login with return URL
			const returnUrl = encodeURIComponent(currentPath);
			goto(`/login?returnUrl=${returnUrl}`);
		} else if (superAdminRoutes.some((route) => currentPath.startsWith(route))) {
			// Super admin route - check role
			if ($isSuperAdmin) {
				authorized = true;
			} else {
				// Not super admin - redirect to dashboard with toast
				toasts.add({
					kind: 'warning',
					title: 'Access Denied',
					subtitle: 'You do not have permission to access that page.'
				});
				goto('/dashboard');
			}
		} else if (adminRoutes.some((route) => currentPath.startsWith(route))) {
			// Admin route - check role
			if ($isAdmin) {
				authorized = true;
			} else {
				// Not admin - redirect to dashboard with toast
				toasts.add({
					kind: 'warning',
					title: 'Access Denied',
					subtitle: 'You do not have permission to access that page.'
				});
				goto('/dashboard');
			}
		} else {
			// Regular protected route - user is authenticated
			authorized = true;
		}
		authChecked = true;
	}
</script>

{#if $auth.isLoading || !authChecked}
	<!-- Show loading skeleton while checking auth -->
	<div class="auth-loading">
		<SkeletonPlaceholder style="width: 100%; height: 100vh;" />
	</div>
{:else if authorized}
	<ToastContainer />
	<AppShell>
		<slot />
	</AppShell>
{/if}

<style>
	.auth-loading {
		width: 100%;
		height: 100vh;
	}
</style>
