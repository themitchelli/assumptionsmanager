<script lang="ts">
	import { onMount } from 'svelte';
	import {
		Grid,
		Row,
		Column,
		Tile,
		TextInput,
		Button,
		SkeletonText,
		ToastNotification,
		InlineLoading
	} from 'carbon-components-svelte';
	import { Edit, Checkmark, Close } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { api } from '$lib/api';
	import { toasts } from '$lib/stores/toast';
	import type { TenantResponse, UpdateTenantRequest } from '$lib/api/types';

	// State
	let tenant: TenantResponse | null = null;
	let loading = true;
	let error: string | null = null;

	// Edit state
	let isEditing = false;
	let editedName = '';
	let isSaving = false;
	let editError: string | null = null;

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'long',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function startEditing() {
		if (tenant) {
			editedName = tenant.name;
			isEditing = true;
			editError = null;
		}
	}

	function cancelEditing() {
		isEditing = false;
		editedName = '';
		editError = null;
	}

	async function saveChanges() {
		if (!tenant || !editedName.trim()) {
			editError = 'Tenant name is required';
			return;
		}

		if (editedName.trim() === tenant.name) {
			cancelEditing();
			return;
		}

		isSaving = true;
		editError = null;

		const updateData: UpdateTenantRequest = {
			name: editedName.trim()
		};

		const response = await api.patch<TenantResponse>(`/tenants/${tenant.id}`, updateData);

		if (response.error) {
			editError = response.error.message;
			isSaving = false;
			return;
		}

		if (response.data) {
			tenant = response.data;
			// Also update auth store with new tenant name
			if ($auth.user) {
				auth.setUser(
					{ ...$auth.user, tenant_name: response.data.name },
					sessionStorage.getItem('auth_token') || ''
				);
			}
			toasts.add({
				kind: 'success',
				title: 'Settings saved',
				subtitle: 'Tenant name has been updated'
			});
		}

		isEditing = false;
		editedName = '';
		isSaving = false;
	}

	async function fetchTenant() {
		loading = true;
		error = null;

		const response = await api.get<TenantResponse>('/tenants/me');

		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			tenant = response.data;
		}

		loading = false;
	}

	onMount(() => {
		breadcrumbs.set([{ label: 'Admin', href: '/admin/users' }, { label: 'Tenant Settings' }]);
		fetchTenant();
	});
</script>

<svelte:head>
	<title>Tenant Settings - Admin - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">Tenant Settings</h1>
			<p class="page-description">View and manage your organization's settings</p>
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

	<Row>
		<Column lg={8} md={6} sm={4}>
			{#if loading}
				<Tile>
					<SkeletonText heading />
					<SkeletonText paragraph lines={3} />
				</Tile>
			{:else if tenant}
				<Tile>
					<div class="settings-section">
						<h3 class="section-title">Organization Details</h3>

						<div class="setting-row">
							<div class="setting-label">Tenant ID</div>
							<div class="setting-value readonly">
								<code>{tenant.id}</code>
							</div>
						</div>

						<div class="setting-row">
							<div class="setting-label">Organization Name</div>
							<div class="setting-value">
								{#if isEditing}
									<div class="edit-container">
										<TextInput
											bind:value={editedName}
											placeholder="Enter organization name"
											invalid={!!editError}
											invalidText={editError || ''}
											disabled={isSaving}
											on:keydown={(e) => {
												if (e.key === 'Enter') saveChanges();
												if (e.key === 'Escape') cancelEditing();
											}}
										/>
										<div class="edit-actions">
											{#if isSaving}
												<InlineLoading description="Saving..." />
											{:else}
												<Button
													kind="ghost"
													size="small"
													icon={Checkmark}
													iconDescription="Save"
													on:click={saveChanges}
												/>
												<Button
													kind="ghost"
													size="small"
													icon={Close}
													iconDescription="Cancel"
													on:click={cancelEditing}
												/>
											{/if}
										</div>
									</div>
								{:else}
									<div class="editable-value">
										<span>{tenant.name}</span>
										<Button
											kind="ghost"
											size="small"
											icon={Edit}
											iconDescription="Edit name"
											on:click={startEditing}
										/>
									</div>
								{/if}
							</div>
						</div>

						<div class="setting-row">
							<div class="setting-label">Created</div>
							<div class="setting-value readonly">{formatDate(tenant.created_at)}</div>
						</div>
					</div>
				</Tile>

				<Tile class="info-tile">
					<div class="info-section">
						<h4>Need help?</h4>
						<p>
							Contact your administrator or support team for assistance with tenant settings that
							cannot be modified here.
						</p>
					</div>
				</Tile>
			{/if}
		</Column>
	</Row>
</Grid>

<style>
	.page-title {
		margin-bottom: 0.5rem;
		font-size: 2rem;
		font-weight: 400;
	}

	.page-description {
		margin-bottom: 1.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	.settings-section {
		padding: 0.5rem;
	}

	.section-title {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 1.5rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--cds-border-subtle-01, #e0e0e0);
	}

	.setting-row {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
	}

	@media (min-width: 672px) {
		.setting-row {
			flex-direction: row;
			align-items: flex-start;
		}

		.setting-label {
			width: 180px;
			flex-shrink: 0;
		}

		.setting-value {
			flex: 1;
		}
	}

	.setting-label {
		font-weight: 500;
		color: var(--cds-text-secondary, #525252);
		padding-top: 0.5rem;
	}

	.setting-value {
		font-size: 0.875rem;
	}

	.setting-value.readonly {
		color: var(--cds-text-primary, #161616);
		padding-top: 0.5rem;
	}

	.setting-value code {
		font-family: 'IBM Plex Mono', monospace;
		font-size: 0.75rem;
		background: var(--cds-layer-accent-01, #e0e0e0);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	.editable-value {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.editable-value span {
		padding-top: 0.5rem;
	}

	.edit-container {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		width: 100%;
		max-width: 400px;
	}

	.edit-actions {
		display: flex;
		gap: 0.25rem;
	}

	:global(.info-tile) {
		margin-top: 1rem;
		background: var(--cds-layer-02, #f4f4f4);
	}

	.info-section h4 {
		font-size: 0.875rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
	}

	.info-section p {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
		margin: 0;
	}
</style>
