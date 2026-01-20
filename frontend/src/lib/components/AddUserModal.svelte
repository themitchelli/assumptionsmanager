<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		Dropdown,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { CreateUserRequest, UserResponse } from '$lib/api/types';

	export let open = false;
	export let existingEmails: string[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		created: UserResponse;
	}>();

	// Form state
	let email = '';
	let selectedRole = 'viewer';
	let submitting = false;
	let error: string | null = null;

	// Validation state
	let emailError: string | null = null;
	let emailTouched = false;

	const roleOptions = [
		{ id: 'viewer', text: 'Viewer - Can view data only' },
		{ id: 'analyst', text: 'Analyst - Can view and edit data' },
		{ id: 'admin', text: 'Admin - Full access including user management' }
	];

	// Email validation
	const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

	function validateEmail(value: string): string | null {
		if (!value.trim()) {
			return 'Email is required';
		}
		if (!emailRegex.test(value)) {
			return 'Please enter a valid email address';
		}
		if (existingEmails.some((e) => e.toLowerCase() === value.toLowerCase())) {
			return 'A user with this email already exists';
		}
		return null;
	}

	function handleEmailInput() {
		emailTouched = true;
		emailError = validateEmail(email);
	}

	function handleEmailBlur() {
		emailTouched = true;
		emailError = validateEmail(email);
	}

	$: isValid = email.trim() && !validateEmail(email);

	async function handleSubmit() {
		// Final validation
		emailError = validateEmail(email);
		if (emailError) {
			emailTouched = true;
			return;
		}

		submitting = true;
		error = null;

		const userData: CreateUserRequest = {
			email: email.trim(),
			role: selectedRole as 'viewer' | 'analyst' | 'admin'
		};

		const response = await api.post<UserResponse>('/users', userData);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			dispatch('created', response.data);
			resetForm();
		}

		submitting = false;
	}

	function resetForm() {
		email = '';
		selectedRole = 'viewer';
		emailError = null;
		emailTouched = false;
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
	modalHeading="Add User"
	primaryButtonText="Add User"
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
			Add a new user to your organization. They will receive an email with instructions to set up
			their password.
		</p>

		<div class="form-group">
			<TextInput
				id="email"
				labelText="Email address"
				placeholder="user@example.com"
				bind:value={email}
				invalid={emailTouched && !!emailError}
				invalidText={emailError || undefined}
				on:input={handleEmailInput}
				on:blur={handleEmailBlur}
				disabled={submitting}
			/>
		</div>

		<div class="form-group">
			<Dropdown
				titleText="Role"
				bind:selectedId={selectedRole}
				items={roleOptions}
				disabled={submitting}
			/>
			<p class="helper-text">Select the permission level for this user</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Creating user..." />
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
