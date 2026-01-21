<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';

	export let open = false;
	export let tableId: string;
	export let tableName: string;
	export let rowCount: number;

	const dispatch = createEventDispatcher<{
		close: void;
		deleted: void;
	}>();

	// Form state
	let confirmationName = '';
	let submitting = false;
	let error: string | null = null;

	// Reset form when modal opens/closes
	$: if (open) {
		confirmationName = '';
		error = null;
	}

	// Check if name confirmation matches (case-sensitive)
	$: nameMatches = confirmationName === tableName;

	async function handleSubmit() {
		if (!nameMatches) return;

		submitting = true;
		error = null;

		const response = await api.delete(`/tables/${tableId}`);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		dispatch('deleted');
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
	modalHeading="Delete Table"
	primaryButtonText="Delete Table"
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

		<div class="warning-section">
			<p class="warning-title">Delete "{tableName}"?</p>
			<p class="warning-impact">
				This will permanently remove all {rowCount} row{rowCount !== 1 ? 's' : ''}.
			</p>
		</div>

		<div class="form-group">
			<TextInput
				id="confirmation-name"
				labelText="Type the table name to confirm"
				placeholder={tableName}
				bind:value={confirmationName}
				disabled={submitting}
				invalid={confirmationName.length > 0 && !nameMatches}
				invalidText="Table name does not match"
			/>
			<p class="helper-text">
				This action cannot be undone. All data in this table will be permanently deleted.
			</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Deleting table..." />
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
