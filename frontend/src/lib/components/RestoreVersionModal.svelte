<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextInput,
		InlineLoading,
		InlineNotification
	} from 'carbon-components-svelte';
	import { api } from '$lib/api';
	import type { TableDetailResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;
	export let tableName: string;
	export let versionId: string;
	export let versionNumber: number;
	export let approvalStatus: string | undefined;

	const dispatch = createEventDispatcher<{
		close: void;
		restored: TableDetailResponse;
	}>();

	// Form state
	let confirmationValue = '';
	let submitting = false;
	let error: string | null = null;

	// Reset form when modal opens/closes
	$: if (open) {
		confirmationValue = '';
		error = null;
	}

	// Confirmation requires typing the version number
	$: expectedValue = `v${versionNumber}`;
	$: valueMatches = confirmationValue === expectedValue;

	// Check if this is restoring to a non-approved version
	$: isNonApproved = approvalStatus !== 'approved';

	async function handleSubmit() {
		if (!valueMatches) return;

		submitting = true;
		error = null;

		const response = await api.post<TableDetailResponse>(
			`/tables/${tableId}/versions/${versionId}/restore`
		);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			dispatch('restored', response.data);
		}
		submitting = false;
	}

	function handleClose() {
		if (!submitting) {
			confirmationValue = '';
			error = null;
			dispatch('close');
		}
	}
</script>

<Modal
	bind:open
	modalHeading="Restore Version"
	primaryButtonText="Restore Version"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!valueMatches || submitting}
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
			<p class="warning-title">Restore to version {versionNumber}?</p>
			<p class="warning-impact">
				This will overwrite the current table data with the snapshot from v{versionNumber}.
			</p>
		</div>

		<div class="context-info">
			<div class="info-row">
				<span class="label">Table:</span>
				<span class="value">{tableName}</span>
			</div>
			<div class="info-row">
				<span class="label">Restoring to:</span>
				<span class="value version">v{versionNumber}</span>
			</div>
		</div>

		{#if isNonApproved}
			<InlineNotification
				kind="warning"
				title="Warning"
				subtitle="This version is not approved. Restoring it will overwrite any approved data. A new draft version will be created automatically after restore for audit trail."
				lowContrast
				hideCloseButton
			/>
		{:else}
			<InlineNotification
				kind="info"
				title="Restoring will create a new draft version"
				subtitle="A new draft version snapshot will be created automatically after restore to maintain the audit trail. The new version will require approval before it can be used in production."
				lowContrast
				hideCloseButton
			/>
		{/if}

		<div class="form-group">
			<TextInput
				id="confirmation-version"
				labelText="Type the version number to confirm (e.g., v{versionNumber})"
				placeholder={expectedValue}
				bind:value={confirmationValue}
				disabled={submitting}
				invalid={confirmationValue.length > 0 && !valueMatches}
				invalidText="Version number does not match"
			/>
			<p class="helper-text">
				This action will replace all current data in the table with the data from this version.
			</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Restoring version..." />
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

	.context-info {
		padding: 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.info-row {
		display: flex;
		gap: 0.5rem;
		margin-bottom: 0.5rem;
	}

	.info-row:last-child {
		margin-bottom: 0;
	}

	.label {
		font-weight: 500;
		color: var(--cds-text-secondary, #525252);
		min-width: 100px;
	}

	.value {
		color: var(--cds-text-primary, #161616);
	}

	.value.version {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
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
