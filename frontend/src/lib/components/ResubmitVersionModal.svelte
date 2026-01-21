<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextArea,
		InlineLoading,
		InlineNotification,
		Button,
		SkeletonText
	} from 'carbon-components-svelte';
	import { Renew, WarningAltFilled } from 'carbon-icons-svelte';
	import { api } from '$lib/api';
	import type { SubmitApprovalRequest, VersionListResponse, ApprovalHistoryEntry } from '$lib/api/types';

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
	let touched = false;

	// Rejection reason state
	let rejectionReason: string | null = null;
	let rejectionBy: string | null = null;
	let rejectionAt: string | null = null;
	let loadingHistory = true;
	let historyError: string | null = null;

	const MIN_COMMENT_LENGTH = 10;
	const MAX_COMMENT_LENGTH = 500;

	// Validation - comment is required for resubmission
	$: commentTooShort = touched && comment.trim().length < MIN_COMMENT_LENGTH;
	$: commentTooLong = comment.trim().length > MAX_COMMENT_LENGTH;
	$: isValid = comment.trim().length >= MIN_COMMENT_LENGTH && !commentTooLong;

	// Fetch rejection reason from approval history
	async function fetchRejectionReason() {
		loadingHistory = true;
		historyError = null;

		const response = await api.get<ApprovalHistoryEntry[]>(
			`/tables/${tableId}/versions/${versionId}/history`
		);

		if (response.error) {
			historyError = response.error.message;
			loadingHistory = false;
			return;
		}

		if (response.data) {
			// Find the most recent rejection entry
			const rejectionEntry = response.data
				.filter(entry => entry.to_status === 'rejected')
				.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];

			if (rejectionEntry) {
				rejectionReason = rejectionEntry.comment || 'No reason provided';
				rejectionBy = rejectionEntry.changed_by_name;
				rejectionAt = rejectionEntry.created_at;
			}
		}

		loadingHistory = false;
	}

	// Format datetime for display
	function formatDateTime(dateStr: string): string {
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

		const submitData: SubmitApprovalRequest = {
			comment: comment.trim()
		};

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
		touched = false;
		rejectionReason = null;
		rejectionBy = null;
		rejectionAt = null;
		loadingHistory = true;
		historyError = null;
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

	// When modal opens, fetch rejection reason
	$: if (open && versionId) {
		fetchRejectionReason();
	}
</script>

<Modal
	bind:open
	modalHeading="Resubmit for Approval"
	primaryButtonText="Resubmit"
	secondaryButtonText="Cancel"
	primaryButtonDisabled={!isValid || submitting || loadingHistory}
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

		<!-- Previous rejection reason -->
		<div class="rejection-section">
			<div class="rejection-header">
				<WarningAltFilled size={20} class="rejection-icon" />
				<h4>Previous Rejection Reason</h4>
			</div>
			{#if loadingHistory}
				<SkeletonText paragraph lines={2} />
			{:else if historyError}
				<InlineNotification
					kind="warning"
					title="Could not load rejection reason"
					subtitle={historyError}
					lowContrast
					hideCloseButton
				/>
			{:else if rejectionReason}
				<div class="rejection-content">
					<p class="rejection-reason">{rejectionReason}</p>
					{#if rejectionBy && rejectionAt}
						<p class="rejection-meta">
							Rejected by {rejectionBy} on {formatDateTime(rejectionAt)}
						</p>
					{/if}
				</div>
			{:else}
				<p class="no-reason">No rejection reason found.</p>
			{/if}
		</div>

		<p class="modal-description">
			Resubmit this version for approval after addressing the feedback above.
		</p>

		<div class="form-group">
			<TextArea
				id="resubmit-comment"
				labelText="Describe changes made"
				placeholder="Explain what changes you made to address the feedback..."
				bind:value={comment}
				invalid={commentTooShort || commentTooLong}
				invalidText={commentTooShort
					? `Comment must be at least ${MIN_COMMENT_LENGTH} characters`
					: `Comment must be ${MAX_COMMENT_LENGTH} characters or less`}
				disabled={submitting}
				rows={4}
				maxlength={MAX_COMMENT_LENGTH + 10}
				on:blur={() => (touched = true)}
			/>
			<p class="helper-text">
				{comment.trim().length}/{MAX_COMMENT_LENGTH} characters (minimum {MIN_COMMENT_LENGTH})
			</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Resubmitting for approval..." />
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

	.rejection-section {
		background: var(--cds-notification-background-warning, #fcf4d6);
		border-left: 4px solid var(--cds-support-warning, #f1c21b);
		padding: 1rem;
		border-radius: 0 4px 4px 0;
	}

	.rejection-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.75rem;
	}

	.rejection-header h4 {
		margin: 0;
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--cds-text-primary, #161616);
	}

	.rejection-header :global(.rejection-icon) {
		color: var(--cds-support-warning, #f1c21b);
	}

	.rejection-content {
		padding-left: 0.25rem;
	}

	.rejection-reason {
		margin: 0 0 0.5rem 0;
		color: var(--cds-text-primary, #161616);
		white-space: pre-wrap;
		word-break: break-word;
	}

	.rejection-meta {
		margin: 0;
		font-size: 0.75rem;
		color: var(--cds-text-secondary, #525252);
		font-style: italic;
	}

	.no-reason {
		margin: 0;
		color: var(--cds-text-secondary, #525252);
		font-style: italic;
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
