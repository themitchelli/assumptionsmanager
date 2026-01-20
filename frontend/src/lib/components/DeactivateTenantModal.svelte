<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { TenantListItem, TenantDetailResponse, UpdateTenantRequest } from '$lib/api/types';

	export let open = false;
	export let tenant: TenantListItem | TenantDetailResponse | null = null;

	const dispatch = createEventDispatcher<{
		close: void;
		deactivated: { id: string; status: 'inactive' };
	}>();

	// Form state
	let confirmationName = '';
	let submitting = false;
	let error: string | null = null;

	// Reset form when modal opens/closes or tenant changes
	$: if (open || tenant) {
		confirmationName = '';
		error = null;
	}

	// Check if tenant name confirmation matches (case-insensitive)
	$: nameMatches = tenant && confirmationName.toLowerCase() === tenant.name.toLowerCase();

	async function handleSubmit() {
		if (!tenant || !nameMatches) return;

		submitting = true;
		error = null;

		const response = await api.patch<TenantDetailResponse>(
			`/tenants/${tenant.id}`,
			{ status: 'inactive' } as UpdateTenantRequest
		);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		dispatch('deactivated', { id: tenant.id, status: 'inactive' });
		submitting = false;
	}

	function handleClose() {
		if (!submitting) {
			confirmationName = '';
			error = null;
			dispatch('close');
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Deactivate Tenant"
	primaryButtonText="Deactivate Tenant"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!nameMatches || submitting}
	danger
	on:click:button--secondary={handleClose}
	on:close={handleClose}
	on:submit={handleSubmit}
	hasForm
>
	<div class="modal-content">
		{#if error}
			<InlineNotification
				kind="error"
				title="Error"
				subtitle={error}
				lowContrast
				hideCloseButton={false}
				on:close={() => (error = null)}
			/>
		{/if}

		{#if tenant}
			<div class="warning-section">
				<p class="warning-title">Are you sure you want to deactivate {tenant.name}?</p>
				<p class="warning-impact">All users in {tenant.name} will be unable to log in.</p>
			</div>

			<div class="tenant-info">
				<p><strong>Tenant Name:</strong> {tenant.name}</p>
				<p><strong>Users:</strong> {tenant.user_count}</p>
				<p><strong>Current Status:</strong> {tenant.status === 'active' ? 'Active' : 'Inactive'}</p>
			</div>

			<div class="form-group">
				<TextInput
					id="confirmation-name"
					labelText="Type the tenant name to confirm"
					placeholder={tenant.name}
					bind:value={confirmationName}
					disabled={submitting}
					invalid={confirmationName.length > 0 && !nameMatches}
					invalidText="Tenant name does not match"
				/>
				<p class="helper-text">
					This will immediately suspend access for all users in this tenant.
					You can reactivate the tenant at any time to restore access.
				</p>
			</div>

			{#if submitting}
				<div class="loading-container">
					<InlineLoading description="Deactivating tenant..." />
				</div>
			{/if}
		{/if}
	</div>
</Modal>

<style>
	.modal-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.warning-section {
		padding: 1rem;
		background: var(--cds-support-error-inverse, #fff1f1);
		border-left: 3px solid var(--cds-support-error, #da1e28);
		border-radius: 0 4px 4px 0;
	}

	.warning-title {
		font-weight: 600;
		color: var(--cds-text-primary, #161616);
		margin-bottom: 0.25rem;
	}

	.warning-impact {
		color: var(--cds-support-error, #da1e28);
		font-size: 0.875rem;
	}

	.tenant-info {
		padding: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.tenant-info p {
		margin: 0.25rem 0;
		font-size: 0.875rem;
	}

	.form-group {
		display: flex;
		flex-direction: column;
	}

	.helper-text {
		font-size: 0.75rem;
		color: var(--cds-text-helper, #6f6f6f);
		margin-top: 0.25rem;
	}

	.loading-container {
		display: flex;
		justify-content: flex-start;
		margin-top: 0.5rem;
	}

	:global(.bx--modal-content) {
		overflow: visible;
	}
</style>
