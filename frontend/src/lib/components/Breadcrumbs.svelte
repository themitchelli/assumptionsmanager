<script lang="ts">
	import { Breadcrumb, BreadcrumbItem } from 'carbon-components-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
</script>

{#if $breadcrumbs.length > 0}
	<Breadcrumb noTrailingSlash>
		{#each $breadcrumbs as crumb, index}
			{#if crumb.href && index < $breadcrumbs.length - 1}
				<BreadcrumbItem href={crumb.href}>{crumb.label}</BreadcrumbItem>
			{:else}
				<BreadcrumbItem isCurrentPage>{crumb.label}</BreadcrumbItem>
			{/if}
		{/each}
	</Breadcrumb>
{/if}

<style>
	:global(.bx--breadcrumb) {
		margin-bottom: 1rem;
	}
</style>
