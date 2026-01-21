<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { RowResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;
	export let rows: RowResponse[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		deleted: string[]; // array of deleted row ids
	}>();

	// Form state
	let submitting = false;
	let error: string | null = null;
	let failedRowIds: string[] = [];

	// Reset state when modal opens
	$: if (open) {
		error = null;
		failedRowIds = [];
	}

	async function handleSubmit() {
		if (rows.length === 0) return;

		submitting = true;
		error = null;
		failedRowIds = [];

		const deletedIds: string[] = [];
		const errors: string[] = [];

		// Delete each row
		for (const row of rows) {
			const response = await api.delete(`/tables/${tableId}/rows/${row.id}`);
			if (response.error) {
				errors.push(`Row ${row.row_index}: ${response.error.message}`);
				failedRowIds.push(row.id);
			} else {
				deletedIds.push(row.id);
			}
		}

		if (errors.length > 0 && deletedIds.length === 0) {
			// All failed
			error = `Failed to delete rows:\n${errors.join('\n')}`;
			submitting = false;
			return;
		}

		if (errors.length > 0) {
			// Partial success
			error = `Some rows could not be deleted:\n${errors.join('\n')}`;
		}

		if (deletedIds.length > 0) {
			dispatch('deleted', deletedIds);
		}

		submitting = false;
	}

	function handleClose() {
		if (!submitting) {
			dispatch('close');
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Delete Rows"
	primaryButtonText="Delete {rows.length} Row{rows.length !== 1 ? 's' : ''}"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={submitting || rows.length === 0}
	danger
	on:click:button--secondary={handleClose}
	on:close={handleClose}
	on:submit={handleSubmit}
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
			<p class="warning-title">Delete {rows.length} row{rows.length !== 1 ? 's' : ''}?</p>
			<p class="warning-impact">This action cannot be undone.</p>
		</div>

		{#if rows.length > 0}
			<div class="rows-info">
				<p class="rows-label">Rows to be deleted:</p>
				<div class="rows-list">
					{#if rows.length <= 10}
						{#each rows as row}
							<span class="row-badge" class:failed={failedRowIds.includes(row.id)}>
								Row {row.row_index}
							</span>
						{/each}
					{:else}
						<span class="rows-summary">
							Rows {rows[0].row_index} - {rows[rows.length - 1].row_index}
							({rows.length} rows total)
						</span>
					{/if}
				</div>
			</div>
		{/if}

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Deleting rows..." />
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

	.rows-info {
		padding: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.rows-label {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 0.5rem;
	}

	.rows-list {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.row-badge {
		display: inline-block;
		padding: 0.25rem 0.5rem;
		background: var(--cds-layer-02, #ffffff);
		border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
		border-radius: 4px;
		font-size: 0.75rem;
		font-weight: 500;
	}

	.row-badge.failed {
		background: var(--cds-support-error-inverse, #fff1f1);
		border-color: var(--cds-support-error, #da1e28);
		color: var(--cds-support-error, #da1e28);
	}

	.rows-summary {
		font-size: 0.875rem;
		color: var(--cds-text-primary, #161616);
	}

	.loading-container {
		display: flex;
		justify-content: flex-start;
		margin-top: 0.5rem;
	}
</style>
