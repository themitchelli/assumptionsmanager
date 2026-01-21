<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextArea,
		InlineLoading,
		InlineNotification,
		Button
	} from 'carbon-components-svelte';
	import { Renew } from 'carbon-icons-svelte';
	import { api } from '$lib/api';
	import type { SubmitApprovalRequest, VersionListResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;
	export let tableName: string;
	export let versionId: string;
	export let versionNumber: number;

	const dispatch = createEventDispatcher<{
		close: void;
		submitted: VersionListResponse;
	}>();

	// Form state
	let comment = '';
	let submitting = false;
	let error: string | null = null;

	const MAX_COMMENT_LENGTH = 500;

	// Validation - comment is optional for submit
	$: commentTooLong = comment.trim().length > MAX_COMMENT_LENGTH;
	$: isValid = !commentTooLong;

	async function handleSubmit() {
		if (commentTooLong) {
			return;
		}

		submitting = true;
		error = null;

		const submitData: SubmitApprovalRequest = {};
		if (comment.trim()) {
			submitData.comment = comment.trim();
		}

		const response = await api.post<VersionListResponse>(
			`/tables/${tableId}/versions/${versionId}/submit`,
			submitData
		);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			dispatch('submitted', response.data);
			resetForm();
		}

		submitting = false;
	}

	async function handleRetry() {
		error = null;
		await handleSubmit();
	}

	function resetForm() {
		comment = '';
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
	modalHeading="Submit for Approval"
	primaryButtonText="Submit"
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
			>
				<svelte:fragment slot="actions">
					<Button
						kind="ghost"
						size="small"
						icon={Renew}
						on:click={handleRetry}
						disabled={submitting}
					>
						Retry
					</Button>
				</svelte:fragment>
			</InlineNotification>
		{/if}

		<div class="confirmation-info">
			<div class="info-row">
				<span class="label">Table:</span>
				<span class="value">{tableName}</span>
			</div>
			<div class="info-row">
				<span class="label">Version:</span>
				<span class="value version-number">v{versionNumber}</span>
			</div>
		</div>

		<p class="modal-description">
			Submit this version for admin approval. Once submitted, the version will be reviewed by an
			administrator who can approve or reject it.
		</p>

		<div class="form-group">
			<TextArea
				id="submit-comment"
				labelText="Comment (optional)"
				placeholder="Add any notes for the reviewer..."
				bind:value={comment}
				invalid={commentTooLong}
				invalidText={`Comment must be ${MAX_COMMENT_LENGTH} characters or less`}
				disabled={submitting}
				rows={3}
				maxlength={MAX_COMMENT_LENGTH + 10}
			/>
			<p class="helper-text">{comment.trim().length}/{MAX_COMMENT_LENGTH} characters</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Submitting for approval..." />
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

	.confirmation-info {
		background: var(--cds-layer-01, #f4f4f4);
		padding: 1rem;
		border-radius: 4px;
	}

	.info-row {
		display: flex;
		margin-bottom: 0.5rem;
	}

	.info-row:last-child {
		margin-bottom: 0;
	}

	.label {
		font-weight: 600;
		min-width: 80px;
		color: var(--cds-text-secondary, #525252);
	}

	.value {
		color: var(--cds-text-primary, #161616);
	}

	.version-number {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}

	.modal-description {
		color: var(--cds-text-secondary, #525252);
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
