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
	import type { CreateColumnRequest, ColumnResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;
	export let existingColumnNames: string[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		created: ColumnResponse;
	}>();

	// Form state
	let name = '';
	let dataType = 'text';
	let submitting = false;
	let error: string | null = null;

	// Validation state
	let nameError: string | null = null;
	let nameTouched = false;

	const MAX_NAME_LENGTH = 100;

	// Data type options for dropdown
	const dataTypeOptions = [
		{ id: 'text', text: 'Text' },
		{ id: 'integer', text: 'Integer' },
		{ id: 'decimal', text: 'Decimal' },
		{ id: 'date', text: 'Date' },
		{ id: 'boolean', text: 'Boolean' }
	];


	function validateName(value: string): string | null {
		const trimmed = value.trim();
		if (!trimmed) {
			return 'Column name is required';
		}
		if (trimmed.length > MAX_NAME_LENGTH) {
			return `Column name must be ${MAX_NAME_LENGTH} characters or less`;
		}
		// Only allow letters, numbers, underscores, and spaces
		if (!/^[\w\s]+$/u.test(trimmed)) {
			return 'Column name can only contain letters, numbers, underscores, and spaces';
		}
		if (existingColumnNames.some((n) => n.toLowerCase() === trimmed.toLowerCase())) {
			return 'A column with this name already exists';
		}
		return null;
	}

	function handleNameInput() {
		nameTouched = true;
		nameError = validateName(name);
	}

	function handleNameBlur() {
		nameTouched = true;
		nameError = validateName(name);
	}

	function handleDataTypeSelect(e: CustomEvent<{ selectedItem: { id: string; text: string } }>) {
		dataType = e.detail.selectedItem.id;
	}

	$: isValid = name.trim() && !validateName(name);

	async function handleSubmit() {
		// Final validation
		nameError = validateName(name);
		if (nameError) {
			nameTouched = true;
			return;
		}

		submitting = true;
		error = null;

		const columnData: CreateColumnRequest = {
			name: name.trim(),
			data_type: dataType as CreateColumnRequest['data_type']
		};

		const response = await api.post<ColumnResponse>(`/tables/${tableId}/columns`, columnData);

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
		name = '';
		dataType = 'text';
		nameError = null;
		nameTouched = false;
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
	modalHeading="Add Column"
	primaryButtonText="Add Column"
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
			Add a new column to the table. The column will be added to the right side of the grid.
		</p>

		<div class="form-group">
			<TextInput
				id="column-name"
				labelText="Column name"
				placeholder="e.g., Age Band"
				bind:value={name}
				invalid={nameTouched && !!nameError}
				invalidText={nameError || undefined}
				on:input={handleNameInput}
				on:blur={handleNameBlur}
				disabled={submitting}
				maxlength={MAX_NAME_LENGTH}
			/>
			<p class="helper-text">{name.trim().length}/{MAX_NAME_LENGTH} characters</p>
		</div>

		<div class="form-group">
			<Dropdown
				titleText="Data type"
				selectedId={dataType}
				items={dataTypeOptions}
				on:select={handleDataTypeSelect}
				disabled={submitting}
			/>
			<p class="helper-text">
				{#if dataType === 'text'}
					Text: Any string value
				{:else if dataType === 'integer'}
					Integer: Whole numbers (e.g., 42, -10)
				{:else if dataType === 'decimal'}
					Decimal: Numbers with decimals (e.g., 3.14, -0.5)
				{:else if dataType === 'date'}
					Date: Dates in YYYY-MM-DD format
				{:else if dataType === 'boolean'}
					Boolean: True or False values
				{/if}
			</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Adding column..." />
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
