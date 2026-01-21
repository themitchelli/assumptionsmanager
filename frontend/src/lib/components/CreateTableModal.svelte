<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		TextArea,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { CreateTableRequest, TableResponse } from '$lib/api/types';

	export let open = false;
	export let existingTableNames: string[] = [];

	const dispatch = createEventDispatcher<{
		close: void;
		created: TableResponse;
	}>();

	// Form state
	let name = '';
	let description = '';
	let submitting = false;
	let error: string | null = null;

	// Validation state
	let nameError: string | null = null;
	let nameTouched = false;

	const MAX_NAME_LENGTH = 100;

	function validateName(value: string): string | null {
		const trimmed = value.trim();
		if (!trimmed) {
			return 'Table name is required';
		}
		if (trimmed.length > MAX_NAME_LENGTH) {
			return `Table name must be ${MAX_NAME_LENGTH} characters or less`;
		}
		if (existingTableNames.some((n) => n.toLowerCase() === trimmed.toLowerCase())) {
			return 'A table with this name already exists';
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

		const tableData: CreateTableRequest = {
			name: name.trim(),
			description: description.trim() || undefined,
			columns: [] // Start with no columns - user can add via Add Column button
		};

		const response = await api.post<TableResponse>('/tables', tableData);

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
		description = '';
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
	modalHeading="Create Table"
	primaryButtonText="Create Table"
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
			Create a new assumption table. You can add columns and data after the table is created.
		</p>

		<div class="form-group">
			<TextInput
				id="table-name"
				labelText="Table name"
				placeholder="e.g., Mortality Rates 2024"
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
			<TextArea
				id="table-description"
				labelText="Description (optional)"
				placeholder="Describe the purpose of this table..."
				bind:value={description}
				disabled={submitting}
				rows={3}
			/>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Creating table..." />
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
