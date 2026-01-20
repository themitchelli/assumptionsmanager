<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		Tile,
		Button,
		SkeletonText,
		ToastNotification,
		Tag
	} from 'carbon-components-svelte';
	import { ArrowLeft, UserMultiple } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { api } from '$lib/api';
	import type { TenantDetailResponse } from '$lib/api/types';

	// State
	let tenant: TenantDetailResponse | null = null;
	let loading = true;
	let error: string | null = null;

	$: tenantId = $page.params.id;

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getStatusDisplay(status: string): { text: string; type: 'green' | 'gray' } {
		switch (status) {
			case 'active':
				return { text: 'Active', type: 'green' };
			case 'inactive':
				return { text: 'Inactive', type: 'gray' };
			default:
				return { text: 'Unknown', type: 'gray' };
		}
	}

	async function fetchTenant() {
		loading = true;
		error = null;

		const response = await api.get<TenantDetailResponse>(`/tenants/${tenantId}`);

		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			tenant = response.data;
		}

		loading = false;
	}

	onMount(() => {
		breadcrumbs.set([
			{ label: 'Admin', href: '/admin/users' },
			{ label: 'All Tenants', href: '/admin/tenants' },
			{ label: 'Tenant Details' }
		]);
		fetchTenant();
	});
</script>

<svelte:head>
	<title>{tenant?.name ?? 'Tenant Details'} - Admin - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<Button kind="ghost" icon={ArrowLeft} on:click={() => goto('/admin/tenants')}>
				Back to All Tenants
			</Button>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error"
					subtitle={error}
					lowContrast
					on:close={() => (error = null)}
				/>
			</Column>
		</Row>
	{/if}

	{#if loading}
		<Row>
			<Column>
				<div class="skeleton-container">
					<SkeletonText heading />
					<SkeletonText paragraph lines={5} />
				</div>
			</Column>
		</Row>
	{:else if tenant}
		<Row>
			<Column>
				<div class="tenant-header">
					<h1 class="page-title">{tenant.name}</h1>
					<Tag type={getStatusDisplay(tenant.status).type}>
						{getStatusDisplay(tenant.status).text}
					</Tag>
				</div>
			</Column>
		</Row>

		<Row>
			<Column sm={4} md={4} lg={8}>
				<Tile>
					<h3 class="section-title">Tenant Information</h3>
					<div class="info-grid">
						<div class="info-item">
							<span class="info-label">Tenant ID</span>
							<code class="info-value">{tenant.id}</code>
						</div>
						<div class="info-item">
							<span class="info-label">Name</span>
							<span class="info-value">{tenant.name}</span>
						</div>
						<div class="info-item">
							<span class="info-label">Status</span>
							<span class="info-value">
								<Tag type={getStatusDisplay(tenant.status).type}>
									{getStatusDisplay(tenant.status).text}
								</Tag>
							</span>
						</div>
						<div class="info-item">
							<span class="info-label">Created</span>
							<span class="info-value">{formatDate(tenant.created_at)}</span>
						</div>
						{#if tenant.updated_at}
							<div class="info-item">
								<span class="info-label">Last Updated</span>
								<span class="info-value">{formatDate(tenant.updated_at)}</span>
							</div>
						{/if}
					</div>
				</Tile>
			</Column>

			<Column sm={4} md={4} lg={4}>
				<Tile class="stats-tile">
					<div class="stat-icon">
						<UserMultiple size={32} />
					</div>
					<div class="stat-content">
						<span class="stat-value">{tenant.user_count}</span>
						<span class="stat-label">Total Users</span>
					</div>
				</Tile>
			</Column>
		</Row>
	{/if}
</Grid>

<style>
	.page-title {
		margin-bottom: 0;
		font-size: 2rem;
		font-weight: 400;
	}

	.tenant-header {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin: 1rem 0 1.5rem;
	}

	.section-title {
		margin-bottom: 1rem;
		font-size: 1.125rem;
		font-weight: 600;
	}

	.info-grid {
		display: grid;
		gap: 1rem;
	}

	.info-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.info-label {
		font-size: 0.75rem;
		color: var(--cds-text-secondary, #525252);
		text-transform: uppercase;
		letter-spacing: 0.025em;
	}

	.info-value {
		font-size: 1rem;
	}

	code.info-value {
		font-family: 'IBM Plex Mono', monospace;
		font-size: 0.875rem;
		background: var(--cds-layer-02, #e0e0e0);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	:global(.stats-tile) {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		text-align: center;
		padding: 2rem;
	}

	.stat-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 64px;
		height: 64px;
		border-radius: 50%;
		background: #d0e2ff;
		color: #0043ce;
		margin-bottom: 1rem;
	}

	.stat-content {
		display: flex;
		flex-direction: column;
	}

	.stat-value {
		font-size: 2.5rem;
		font-weight: 600;
		line-height: 1.2;
	}

	.stat-label {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
	}

	.skeleton-container {
		padding: 1rem;
	}
</style>
