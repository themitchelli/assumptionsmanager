<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		Modal,
		TextArea,
		InlineLoading,
		InlineNotification,
		Button
	} from 'carbon-components-svelte';
	import { Renew, WarningAlt } from 'carbon-icons-svelte';
	import { api } from '$lib/api';
	import type { ApproveRequest, VersionListResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;
	export let tableName: string;
	export let versionId: string;
	export let versionNumber: number;
	export let submittedBy: string | undefined = undefined;
	export let submittedAt: string | undefined = undefined;

	const dispatch = createEventDispatcher<{
		close: void;
		approved: VersionListResponse;
	}>();

	// Form state
	let comment = '';
	let submitting = false;
	let error: string | null = null;

	const MAX_COMMENT_LENGTH = 500;

	// Validation - comment is optional for approval
	$: commentTooLong = comment.trim().length > MAX_COMMENT_LENGTH;
	$: isValid = !commentTooLong;

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
		if (commentTooLong) {
			return;
		}

		submitting = true;
		error = null;

		const approveData: ApproveRequest = {};
		if (comment.trim()) {
			approveData.comment = comment.trim();
		}

		const response = await api.post<VersionListResponse>(
			`/tables/${tableId}/versions/${versionId}/approve`,
			approveData
		);

		if (response.error) {
			error = response.error.message;
			submitting = false;
			return;
		}

		if (response.data) {
			dispatch('approved', response.data);
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
	modalHeading="Approve Version"
	primaryButtonText="Approve"
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
			<div class="info-row">
				<span class="label">Submitted by:</span>
				<span class="value">{submittedBy || 'Unknown'}</span>
			</div>
			<div class="info-row">
				<span class="label">Submitted:</span>
				<span class="value">{formatDate(submittedAt)}</span>
			</div>
		</div>

		<div class="warning-banner">
			<WarningAlt size={20} />
			<span>Approved versions cannot be modified or deleted</span>
		</div>

		<p class="modal-description">
			Approve this version to mark it as ready for production use. This action is final and creates
			a permanent audit record.
		</p>

		<div class="form-group">
			<TextArea
				id="approve-comment"
				labelText="Comment (optional)"
				placeholder="Add approval notes..."
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
				<InlineLoading description="Approving version..." />
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

	.warning-banner {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 1rem;
		background: var(--cds-support-warning-background, #fcf4d6);
		border-left: 3px solid var(--cds-support-warning, #f1c21b);
		border-radius: 4px;
	}

	.warning-banner :global(svg) {
		color: var(--cds-support-warning, #f1c21b);
		flex-shrink: 0;
	}

	.warning-banner span {
		color: var(--cds-text-primary, #161616);
		font-weight: 500;
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
