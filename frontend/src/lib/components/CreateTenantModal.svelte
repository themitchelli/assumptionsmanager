<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { CreateTenantWithAdminRequest, TenantCreateResponse, TenantListItem } from '$lib/api/types';

	export let open = false;
	export let existingTenantNames: string[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		created: TenantListItem;
	}>();

	// Form state
	let tenantName = '';
	let adminEmail = '';
	let adminName = '';
	let submitting = false;
	let error: string | null = null;

	// Validation state
	let tenantNameError: string | null = null;
	let tenantNameTouched = false;
	let adminEmailError: string | null = null;
	let adminEmailTouched = false;
	let adminNameError: string | null = null;
	let adminNameTouched = false;

	// Email validation regex
	const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

	function validateTenantName(value: string): string | null {
		const trimmed = value.trim();
		if (!trimmed) {
			return 'Tenant name is required';
		}
		if (trimmed.length < 2) {
			return 'Tenant name must be at least 2 characters';
		}
		if (trimmed.length > 100) {
			return 'Tenant name must be less than 100 characters';
		}
		if (existingTenantNames.some((n) => n.toLowerCase() === trimmed.toLowerCase())) {
			return 'A tenant with this name already exists';
		}
		return null;
	}

	function validateAdminEmail(value: string): string | null {
		if (!value.trim()) {
			return 'Admin email is required';
		}
		if (!emailRegex.test(value)) {
			return 'Please enter a valid email address';
		}
		return null;
	}

	function validateAdminName(value: string): string | null {
		if (!value.trim()) {
			return 'Admin name is required';
		}
		if (value.trim().length < 2) {
			return 'Admin name must be at least 2 characters';
		}
		return null;
	}

	function handleTenantNameInput() {
		tenantNameTouched = true;
		tenantNameError = validateTenantName(tenantName);
	}

	function handleTenantNameBlur() {
		tenantNameTouched = true;
		tenantNameError = validateTenantName(tenantName);
	}

	function handleAdminEmailInput() {
		adminEmailTouched = true;
		adminEmailError = validateAdminEmail(adminEmail);
	}

	function handleAdminEmailBlur() {
		adminEmailTouched = true;
		adminEmailError = validateAdminEmail(adminEmail);
	}

	function handleAdminNameInput() {
		adminNameTouched = true;
		adminNameError = validateAdminName(adminName);
	}

	function handleAdminNameBlur() {
		adminNameTouched = true;
		adminNameError = validateAdminName(adminName);
	}

	$: isValid =
		tenantName.trim() &&
		adminEmail.trim() &&
		adminName.trim() &&
		!validateTenantName(tenantName) &&
		!validateAdminEmail(adminEmail) &&
		!validateAdminName(adminName);

	async function handleSubmit() {
		// Final validation
		tenantNameError = validateTenantName(tenantName);
		adminEmailError = validateAdminEmail(adminEmail);
		adminNameError = validateAdminName(adminName);

		if (tenantNameError || adminEmailError || adminNameError) {
			tenantNameTouched = true;
			adminEmailTouched = true;
			adminNameTouched = true;
			return;
		}

		submitting = true;
		error = null;

		const requestData: CreateTenantWithAdminRequest = {
			name: tenantName.trim(),
			admin_email: adminEmail.trim(),
			admin_name: adminName.trim()
		};

		const response = await api.post<TenantCreateResponse>('/tenants', requestData);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			// Transform response to TenantListItem format for the table
			const newTenant: TenantListItem = {
				id: response.data.id,
				name: response.data.name,
				user_count: 1, // The newly created admin
				status: 'active',
				created_at: response.data.created_at
			};
			dispatch('created', newTenant);
			resetForm();
		}

		submitting = false;
	}

	function resetForm() {
		tenantName = '';
		adminEmail = '';
		adminName = '';
		tenantNameError = null;
		adminEmailError = null;
		adminNameError = null;
		tenantNameTouched = false;
		adminEmailTouched = false;
		adminNameTouched = false;
		error = null;
		submitting = false;
	}

	function handleClose() {
		resetForm();
		dispatch('close');
	}

	function handleModalClose() {
		// Only allow close if not submitting
		if (!submitting) {
			handleClose();
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Create Tenant"
	primaryButtonText="Create Tenant"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!isValid || submitting}
	on:click:button--secondary={handleClose}
	on:close={handleModalClose}
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

		<p class="modal-description">
			Create a new tenant organization. An admin account will be created for the tenant, and
			they will receive instructions to set up their password.
		</p>

		<div class="form-section">
			<h4 class="section-title">Tenant Details</h4>
			<div class="form-group">
				<TextInput
					id="tenant-name"
					labelText="Tenant Name"
					placeholder="Acme Corporation"
					bind:value={tenantName}
					invalid={tenantNameTouched && !!tenantNameError}
					invalidText={tenantNameError || undefined}
					on:input={handleTenantNameInput}
					on:blur={handleTenantNameBlur}
					disabled={submitting}
				/>
			</div>
		</div>

		<div class="form-section">
			<h4 class="section-title">Initial Admin User</h4>
			<div class="form-group">
				<TextInput
					id="admin-name"
					labelText="Admin Name"
					placeholder="John Smith"
					bind:value={adminName}
					invalid={adminNameTouched && !!adminNameError}
					invalidText={adminNameError || undefined}
					on:input={handleAdminNameInput}
					on:blur={handleAdminNameBlur}
					disabled={submitting}
				/>
			</div>

			<div class="form-group">
				<TextInput
					id="admin-email"
					labelText="Admin Email"
					placeholder="admin@acme.com"
					bind:value={adminEmail}
					invalid={adminEmailTouched && !!adminEmailError}
					invalidText={adminEmailError || undefined}
					on:input={handleAdminEmailInput}
					on:blur={handleAdminEmailBlur}
					disabled={submitting}
				/>
				<p class="helper-text">This email will be used to log in as the tenant admin</p>
			</div>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Creating tenant..." />
			</div>
		{/if}
	</div>
</Modal>

<style>
	.modal-content {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.modal-description {
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 0.5rem;
	}

	.form-section {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.section-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--cds-text-primary, #161616);
		margin: 0;
		padding-top: 0.5rem;
		border-top: 1px solid var(--cds-border-subtle-00, #e0e0e0);
	}

	.form-section:first-of-type .section-title {
		border-top: none;
		padding-top: 0;
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
