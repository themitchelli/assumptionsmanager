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
	import type { CreateVersionRequest, VersionListResponse } from '$lib/api/types';

	export let open = false;
	export let tableId: string;

	const dispatch = createEventDispatcher<{
		close: void;
		created: VersionListResponse;
	}>();

	// Form state
	let comment = '';
	let submitting = false;
	let error: string | null = null;

	// Validation state
	let commentError: string | null = null;
	let commentTouched = false;

	const MAX_COMMENT_LENGTH = 500;

	function validateComment(value: string): string | null {
		const trimmed = value.trim();
		if (!trimmed) {
			return 'Comment is required';
		}
		if (trimmed.length > MAX_COMMENT_LENGTH) {
			return `Comment must be ${MAX_COMMENT_LENGTH} characters or less`;
		}
		return null;
	}

	function handleCommentInput() {
		commentTouched = true;
		commentError = validateComment(comment);
	}

	function handleCommentBlur() {
		commentTouched = true;
		commentError = validateComment(comment);
	}

	$: isValid = comment.trim() && !validateComment(comment);

	async function handleSubmit() {
		// Final validation
		commentError = validateComment(comment);
		if (commentError) {
			commentTouched = true;
			return;
		}

		submitting = true;
		error = null;

		const versionData: CreateVersionRequest = {
			comment: comment.trim()
		};

		const response = await api.post<VersionListResponse>(`/tables/${tableId}/versions`, versionData);

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

	async function handleRetry() {
		error = null;
		await handleSubmit();
	}

	function resetForm() {
		comment = '';
		commentError = null;
		commentTouched = false;
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
	modalHeading="Create Snapshot"
	primaryButtonText="Create Snapshot"
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

		<p class="modal-description">
			Create a version snapshot of the current table state. This captures all rows and cell values
			at this point in time.
		</p>

		<div class="form-group">
			<TextArea
				id="snapshot-comment"
				labelText="Comment"
				placeholder="Describe the changes in this version..."
				bind:value={comment}
				invalid={commentTouched && !!commentError}
				invalidText={commentError || undefined}
				on:input={handleCommentInput}
				on:blur={handleCommentBlur}
				disabled={submitting}
				rows={4}
				maxlength={MAX_COMMENT_LENGTH}
			/>
			<p class="helper-text">{comment.trim().length}/{MAX_COMMENT_LENGTH} characters</p>
		</div>

		{#if submitting}
			<div class="loading-container">
				<InlineLoading description="Creating snapshot..." />
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
