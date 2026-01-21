<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		NumberInput,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { RowResponse, CellData } from '$lib/api/types';

	export let open = false;
	export let tableId: string;

	const dispatch = createEventDispatcher<{
		close: void;
		created: RowResponse[];
	}>();

	// Form state
	let rowCount = 5;
	let submitting = false;
	let error: string | null = null;

	const MIN_ROWS = 1;
	const MAX_ROWS = 100;

	$: isValid = rowCount >= MIN_ROWS && rowCount <= MAX_ROWS;

	async function handleSubmit() {
		if (!isValid) return;

		submitting = true;
		error = null;

		// Create empty rows (cells will be empty object)
		const emptyRows: { cells: CellData }[] = Array.from({ length: rowCount }, () => ({
			cells: {}
		}));

		const response = await api.post<RowResponse[]>(`/tables/${tableId}/rows`, { rows: emptyRows });

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
		rowCount = 5;
		error = null;
		submitting = false;
	}

	function handleClose() {
		resetForm();
		dispatch('close');
	}

	function handleModalClose() {
		if (!submitting) {
			handleClose();
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Add Multiple Rows"
	primaryButtonText="Add Rows"
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
			Add multiple empty rows to the table. You can edit the cell values after the rows are created.
		</p>

		<div class="form-group">
			<NumberInput
				id="row-count"
				label="Number of rows"
				bind:value={rowCount}
				min={MIN_ROWS}
				max={MAX_ROWS}
				invalidText="Enter a number between {MIN_ROWS} and {MAX_ROWS}"
				disabled={submitting}
			/>
			<p class="helper-text">Add between {MIN_ROWS} and {MAX_ROWS} rows at once</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Adding {rowCount} row{rowCount !== 1 ? 's' : ''}..." />
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
</style>
