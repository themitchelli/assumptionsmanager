<script lang="ts">
	import { onMount } from 'svelte';
	import { SkeletonText, Tag, Tooltip } from 'carbon-components-svelte';
	import {
		SendAlt,
		Checkmark,
		Close,
		DocumentBlank,
		Time,
		User
	} from 'carbon-icons-svelte';
	import { api } from '$lib/api';
	import type { ApprovalHistoryEntry } from '$lib/api/types';

	export let tableId: string;
	export let versionId: string;

	let history: ApprovalHistoryEntry[] = [];
	let loading = true;
	let error: string | null = null;

	// Fetch approval history
	async function fetchHistory() {
		loading = true;
		error = null;

		const response = await api.get<ApprovalHistoryEntry[]>(
			`/tables/${tableId}/versions/${versionId}/history`
		);

		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			// Reverse to show newest first
			history = [...response.data].reverse();
		}

		loading = false;
	}

	// Format relative time
	function formatRelativeTime(dateStr: string): string {
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffMins = Math.floor(diffMs / 60000);
		const diffHours = Math.floor(diffMs / 3600000);
		const diffDays = Math.floor(diffMs / 86400000);

		if (diffMins < 1) return 'Just now';
		if (diffMins < 60) return `${diffMins}m ago`;
		if (diffHours < 24) return `${diffHours}h ago`;
		if (diffDays < 7) return `${diffDays}d ago`;

		return date.toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	// Format absolute datetime for tooltip
	function formatAbsoluteTime(dateStr: string): string {
		return new Date(dateStr).toLocaleString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Get action label for state transition
	function getActionLabel(
		fromStatus: string | null,
		toStatus: string
	): { label: string; icon: typeof SendAlt; tagType: 'gray' | 'blue' | 'green' | 'red' } {
		if (toStatus === 'submitted') {
			if (fromStatus === 'rejected') {
				return { label: 'Resubmitted', icon: SendAlt, tagType: 'blue' };
			}
			return { label: 'Submitted', icon: SendAlt, tagType: 'blue' };
		}
		if (toStatus === 'approved') {
			return { label: 'Approved', icon: Checkmark, tagType: 'green' };
		}
		if (toStatus === 'rejected') {
			return { label: 'Rejected', icon: Close, tagType: 'red' };
		}
		if (toStatus === 'draft') {
			return { label: 'Created as draft', icon: DocumentBlank, tagType: 'gray' };
		}
		return { label: toStatus, icon: DocumentBlank, tagType: 'gray' };
	}

	onMount(() => {
		fetchHistory();
	});
</script>

<div class="approval-history-panel">
	<h4>Approval History</h4>

	{#if loading}
		<div class="loading-container">
			<SkeletonText paragraph lines={3} />
		</div>
	{:else if error}
		<div class="error-message">
			<p>Failed to load approval history: {error}</p>
		</div>
	{:else if history.length === 0}
		<div class="empty-state">
			<Time size={24} />
			<p>No approval history yet</p>
			<span class="hint">History will appear once approval actions are taken on this version.</span>
		</div>
	{:else}
		<div class="timeline">
			{#each history as entry, index (entry.id)}
				{@const action = getActionLabel(entry.from_status, entry.to_status)}
				<div class="timeline-entry" class:first={index === 0}>
					<div class="timeline-marker">
						<div class="marker-dot" class:approved={entry.to_status === 'approved'} class:rejected={entry.to_status === 'rejected'} class:submitted={entry.to_status === 'submitted'}>
							<svelte:component this={action.icon} size={16} />
						</div>
						{#if index < history.length - 1}
							<div class="marker-line"></div>
						{/if}
					</div>
					<div class="timeline-content">
						<div class="timeline-header">
							<Tag type={action.tagType} size="sm">{action.label}</Tag>
							<Tooltip triggerText={formatRelativeTime(entry.created_at)} direction="top">
								{formatAbsoluteTime(entry.created_at)}
							</Tooltip>
						</div>
						<div class="timeline-user">
							<User size={16} />
							<span>{entry.changed_by_name}</span>
						</div>
						{#if entry.comment}
							<div class="timeline-comment">
								<p>{entry.comment}</p>
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.approval-history-panel {
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
		padding: 1rem;
	}

	h4 {
		font-size: 0.875rem;
		font-weight: 600;
		margin-bottom: 1rem;
		color: var(--cds-text-primary, #161616);
	}

	.loading-container {
		padding: 0.5rem 0;
	}

	.error-message {
		color: var(--cds-support-error, #da1e28);
		font-size: 0.875rem;
	}

	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 1.5rem;
		text-align: center;
		color: var(--cds-text-secondary, #525252);
	}

	.empty-state :global(svg) {
		margin-bottom: 0.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	.empty-state p {
		font-size: 0.875rem;
		margin-bottom: 0.25rem;
	}

	.empty-state .hint {
		font-size: 0.75rem;
		color: var(--cds-text-helper, #6f6f6f);
	}

	.timeline {
		display: flex;
		flex-direction: column;
	}

	.timeline-entry {
		display: flex;
		gap: 0.75rem;
		min-height: 60px;
	}

	.timeline-entry.first .timeline-content {
		padding-top: 0;
	}

	.timeline-marker {
		display: flex;
		flex-direction: column;
		align-items: center;
		width: 24px;
		flex-shrink: 0;
	}

	.marker-dot {
		width: 24px;
		height: 24px;
		border-radius: 50%;
		background: var(--cds-layer-02, #e0e0e0);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		color: var(--cds-text-secondary, #525252);
	}

	.marker-dot.submitted {
		background: var(--cds-support-info-inverse, #0043ce);
		color: white;
	}

	.marker-dot.approved {
		background: var(--cds-support-success, #24a148);
		color: white;
	}

	.marker-dot.rejected {
		background: var(--cds-support-error, #da1e28);
		color: white;
	}

	.marker-line {
		width: 2px;
		flex: 1;
		background: var(--cds-border-subtle-01, #c6c6c6);
		margin-top: 4px;
		margin-bottom: 4px;
	}

	.timeline-content {
		flex: 1;
		padding-bottom: 1rem;
	}

	.timeline-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.25rem;
	}

	.timeline-user {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.75rem;
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 0.25rem;
	}

	.timeline-user :global(svg) {
		color: var(--cds-text-secondary, #525252);
	}

	.timeline-comment {
		background: var(--cds-layer-02, #e0e0e0);
		border-radius: 4px;
		padding: 0.5rem 0.75rem;
		margin-top: 0.5rem;
	}

	.timeline-comment p {
		font-size: 0.75rem;
		color: var(--cds-text-primary, #161616);
		margin: 0;
		white-space: pre-wrap;
		word-break: break-word;
	}
</style>
