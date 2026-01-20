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
	import type { UpdateUserRequest, UserResponse } from '$lib/api/types';

	export let open = false;
	export let user: UserResponse | null = null;

	const dispatch = createEventDispatcher<{
		close: void;
		updated: UserResponse;
	}>();

	// Form state
	let selectedRole = '';
	let submitting = false;
	let error: string | null = null;

	// Role options - super_admin not included (admins cannot promote to super_admin)
	const roleOptions = [
		{ id: 'viewer', text: 'Viewer - Can view data only' },
		{ id: 'analyst', text: 'Analyst - Can view and edit data' },
		{ id: 'admin', text: 'Admin - Full access including user management' }
	];

	// Reset form when user changes
	$: if (user) {
		selectedRole = user.role;
		error = null;
	}

	// Check if role has changed
	$: hasChanged = user && selectedRole !== user.role;

	async function handleSubmit() {
		if (!user || !hasChanged) return;

		submitting = true;
		error = null;

		const updateData: UpdateUserRequest = {
			role: selectedRole as 'viewer' | 'analyst' | 'admin'
		};

		const response = await api.patch<UserResponse>(`/users/${user.id}`, updateData);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			dispatch('updated', response.data);
		}

		submitting = false;
	}

	function handleClose() {
		if (!submitting) {
			error = null;
			dispatch('close');
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Edit User"
	primaryButtonText="Save Changes"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!hasChanged || submitting}
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

		{#if user}
			<p class="modal-description">Update the role for this user.</p>

			<div class="form-group">
				<TextInput
					id="name"
					labelText="Name"
					value={user.name || user.email.split('@')[0]}
					readonly
					disabled
				/>
			</div>

			<div class="form-group">
				<TextInput id="email" labelText="Email" value={user.email} readonly disabled />
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
					<InlineLoading description="Updating user..." />
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
