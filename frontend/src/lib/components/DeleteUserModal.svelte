<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { UserResponse } from '$lib/api/types';

	export let open = false;
	export let user: UserResponse | null = null;

	const dispatch = createEventDispatcher<{
		close: void;
		deleted: string; // user id
	}>();

	// Form state
	let confirmationEmail = '';
	let submitting = false;
	let error: string | null = null;

	// Track previous state to detect transitions
	let prevOpen = false;
	let prevUserId: string | null = null;

	// Reset form when modal opens or user changes
	$: {
		const currentUserId = user?.id ?? null;
		// Only reset when transitioning from closed to open, or when user changes while open
		if ((!prevOpen && open) || (open && currentUserId !== prevUserId)) {
			confirmationEmail = '';
			error = null;
		}
		prevOpen = open;
		prevUserId = currentUserId;
	}

	// Check if email confirmation matches
	$: emailMatches = user && confirmationEmail.toLowerCase() === user.email.toLowerCase();

	async function handleSubmit() {
		if (!user || !emailMatches) return;

		submitting = true;
		error = null;

		const response = await api.delete(`/users/${user.id}`);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		dispatch('deleted', user.id);
		submitting = false;
	}

	function handleClose() {
		if (!submitting) {
			confirmationEmail = '';
			error = null;
			dispatch('close');
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Delete User"
	primaryButtonText="Delete User"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!emailMatches || submitting}
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

		{#if user}
			<div class="warning-section">
				<p class="warning-title">Are you sure you want to remove {user.name || user.email.split('@')[0]}?</p>
				<p class="warning-impact">This user will lose access immediately.</p>
			</div>

			<div class="user-info">
				<p><strong>Name:</strong> {user.name || user.email.split('@')[0]}</p>
				<p><strong>Email:</strong> {user.email}</p>
				<p><strong>Role:</strong> {user.role}</p>
			</div>

			<div class="form-group">
				<TextInput
					id="confirmation-email"
					labelText="Type the user's email to confirm"
					placeholder={user.email}
					bind:value={confirmationEmail}
					disabled={submitting}
					invalid={confirmationEmail.length > 0 && !emailMatches}
					invalidText="Email does not match"
				/>
				<p class="helper-text">This action cannot be undone. The user will need to be re-invited to regain access.</p>
			</div>

			{#if submitting}
				<div class="loading-container">
					<InlineLoading description="Deleting user..." />
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

	.user-info {
		padding: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.user-info p {
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
