<script lang="ts">
	import {
		Header,
		HeaderUtilities,
		HeaderAction,
		HeaderPanelLinks,
		HeaderPanelLink,
		HeaderPanelDivider,
		SideNav,
		SideNavItems,
		SideNavLink,
		SideNavMenu,
		SideNavMenuItem,
		Content,
		SkipToContent,
		SkeletonPlaceholder
	} from 'carbon-components-svelte';
	import Dashboard from 'carbon-icons-svelte/lib/Dashboard.svelte';
	import TableSplit from 'carbon-icons-svelte/lib/TableSplit.svelte';
	import UserAdmin from 'carbon-icons-svelte/lib/UserAdmin.svelte';
	import Settings from 'carbon-icons-svelte/lib/Settings.svelte';
	import UserAvatar from 'carbon-icons-svelte/lib/UserAvatar.svelte';
	import Logout from 'carbon-icons-svelte/lib/Logout.svelte';
	import { page } from '$app/stores';
	import { auth, isAdmin, isSuperAdmin } from '$lib/stores/auth';
	import { isNavigating } from '$lib/stores/navigation';
	import Breadcrumbs from './Breadcrumbs.svelte';

	let isSideNavOpen = false;
	let isUserPanelOpen = false;

	$: currentPath = $page.url.pathname;

	function handleLogout() {
		auth.logout();
		// Redirect will be handled by route guards
		window.location.href = '/login';
	}
</script>

<Header
	company="Assumptions"
	platformName="Manager"
	bind:isSideNavOpen
	href="/dashboard"
>
	<svelte:fragment slot="skip-to-content">
		<SkipToContent />
	</svelte:fragment>

	<HeaderUtilities>
		<HeaderAction bind:isOpen={isUserPanelOpen} icon={UserAvatar}>
			<HeaderPanelLinks>
				{#if $auth.user}
					<HeaderPanelLink class="user-info">
						<span class="user-name">{$auth.user.name || $auth.user.email}</span>
						<span class="user-role">{$auth.user.role}</span>
						{#if $auth.user.tenant_name}
							<span class="user-tenant">{$auth.user.tenant_name}</span>
						{/if}
					</HeaderPanelLink>
					<HeaderPanelDivider />
				{/if}
				<HeaderPanelLink href="/settings">
					<Settings size={16} style="margin-right: 0.5rem" />
					Settings
				</HeaderPanelLink>
				<HeaderPanelDivider />
				<HeaderPanelLink on:click={handleLogout}>
					<Logout size={16} style="margin-right: 0.5rem" />
					Sign out
				</HeaderPanelLink>
			</HeaderPanelLinks>
		</HeaderAction>
	</HeaderUtilities>
</Header>

<SideNav bind:isOpen={isSideNavOpen} rail>
	<SideNavItems>
		<SideNavLink
			icon={Dashboard}
			text="Dashboard"
			href="/dashboard"
			isSelected={currentPath === '/dashboard'}
		/>
		<SideNavLink
			icon={TableSplit}
			text="Tables"
			href="/tables"
			isSelected={currentPath.startsWith('/tables')}
		/>
		{#if $isAdmin}
			<SideNavMenu icon={UserAdmin} text="Admin" expanded={currentPath.startsWith('/admin')}>
				<SideNavMenuItem
					href="/admin/users"
					text="Users"
					isSelected={currentPath === '/admin/users'}
				/>
				<SideNavMenuItem
					href="/admin/tenant"
					text="Tenant Settings"
					isSelected={currentPath === '/admin/tenant'}
				/>
				{#if $isSuperAdmin}
					<SideNavMenuItem
						href="/admin/tenants"
						text="All Tenants"
						isSelected={currentPath === '/admin/tenants'}
					/>
				{/if}
			</SideNavMenu>
		{/if}
	</SideNavItems>
</SideNav>

<Content>
	<Breadcrumbs />
	{#if $isNavigating}
		<div class="loading-container">
			<SkeletonPlaceholder style="width: 100%; height: 200px;" />
		</div>
	{:else}
		<slot />
	{/if}
</Content>

<style>
	:global(.bx--content) {
		padding: 1rem 2rem;
	}

	.loading-container {
		padding-top: 1rem;
	}

	:global(.user-info) {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		padding: 1rem;
		cursor: default;
	}

	:global(.user-info:hover) {
		background-color: transparent;
	}

	:global(.user-name) {
		font-weight: 600;
		font-size: 0.875rem;
	}

	:global(.user-role) {
		font-size: 0.75rem;
		color: var(--cds-text-secondary);
		text-transform: capitalize;
	}

	:global(.user-tenant) {
		font-size: 0.75rem;
		color: var(--cds-text-helper);
	}
</style>
