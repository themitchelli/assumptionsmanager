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
	import type { RejectRequest, VersionListResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;
	export let tableName: string;
	export let versionId: string;
	export let versionNumber: number;
	export let submittedBy: string | undefined = undefined;
	export let submittedAt: string | undefined = undefined;

	const dispatch = createEventDispatcher<{
		close: void;
		rejected: VersionListResponse;
	}>();

	// Form state
	let comment = '';
	let submitting = false;
	let error: string | null = null;
	let touched = false;

	const MIN_COMMENT_LENGTH = 10;
	const MAX_COMMENT_LENGTH = 1000;

	// Validation - comment is required for rejection with min/max length
	$: commentTooShort = touched && comment.trim().length < MIN_COMMENT_LENGTH;
	$: commentTooLong = comment.trim().length > MAX_COMMENT_LENGTH;
	$: isValid = comment.trim().length >= MIN_COMMENT_LENGTH && !commentTooLong;

	// Format submission date for display
	function formatDate(dateStr: string | undefined): string {
		if (!dateStr) return 'Unknown';
		return new Date(dateStr).toLocaleString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	async function handleSubmit() {
		touched = true;

		if (!isValid) {
			return;
		}

		submitting = true;
		error = null;

		const rejectData: RejectRequest = {
			comment: comment.trim()
		};

		const response = await api.post<VersionListResponse>(
			`/tables/${tableId}/versions/${versionId}/reject`,
			rejectData
		);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			dispatch('rejected', response.data);
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
		touched = false;
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

	function handleCommentBlur() {
		touched = true;
	}
</script>

<Modal
	bind:open
	modalHeading="Reject Version"
	primaryButtonText="Reject"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!isValid || submitting}
	danger
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
			<div class="info-row">
				<span class="label">Submitted by:</span>
				<span class="value">{submittedBy || 'Unknown'}</span>
			</div>
			<div class="info-row">
				<span class="label">Submitted:</span>
				<span class="value">{formatDate(submittedAt)}</span>
			</div>
		</div>

		<p class="modal-description">
			Rejecting this version will require the submitter to address your feedback and resubmit.
			Please provide clear feedback on what needs to be fixed.
		</p>

		<div class="form-group">
			<TextArea
				id="reject-comment"
				labelText="Rejection reason (required)"
				placeholder="Explain what needs to be fixed before resubmission..."
				bind:value={comment}
				invalid={commentTooShort || commentTooLong}
				invalidText={commentTooShort
					? `Comment must be at least ${MIN_COMMENT_LENGTH} characters`
					: `Comment must be ${MAX_COMMENT_LENGTH} characters or less`}
				disabled={submitting}
				rows={4}
				maxlength={MAX_COMMENT_LENGTH + 10}
				on:blur={handleCommentBlur}
			/>
			<p class="helper-text">
				{comment.trim().length}/{MAX_COMMENT_LENGTH} characters (minimum {MIN_COMMENT_LENGTH})
			</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Rejecting version..." />
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
		min-width: 100px;
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
