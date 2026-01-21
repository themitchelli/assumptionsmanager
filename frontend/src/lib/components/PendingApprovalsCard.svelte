<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Tile, SkeletonText, Tag, Link } from 'carbon-components-svelte';
	import { Time, ChevronRight, Checkmark } from 'carbon-icons-svelte';
	import { api } from '$lib/api';
	import type { PendingApprovalsResponse, PendingApprovalItem } from '$lib/api/types';

	// Maximum items to show in the card
	const MAX_ITEMS = 5;

	let pendingApprovals: PendingApprovalItem[] = [];
	let totalCount = 0;
	let loading = true;
	let error: string | null = null;

	// Fetch pending approvals
	async function fetchPendingApprovals() {
		loading = true;
		error = null;

		const response = await api.get<PendingApprovalsResponse>(
			`/versions/pending?limit=${MAX_ITEMS}`
		);

		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			pendingApprovals = response.data.items;
			totalCount = response.data.total_count;
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
			month: 'short'
		});
	}

	// Navigate to version detail page
	function handleItemClick(item: PendingApprovalItem) {
		goto(`/tables/${item.table_id}/versions`);
	}

	onMount(() => {
		fetchPendingApprovals();
	});
</script>

<Tile class="pending-approvals-card">
	<div class="card-header">
		<h3 class="card-title">Pending Approvals</h3>
		{#if !loading && totalCount > 0}
			<Tag type="blue" size="sm">{totalCount}</Tag>
		{/if}
	</div>

	{#if loading}
		<div class="loading-container">
			<SkeletonText paragraph lines={3} />
		</div>
	{:else if error}
		<div class="error-message">
			<p>Failed to load: {error}</p>
		</div>
	{:else if pendingApprovals.length === 0}
		<div class="empty-state">
			<Checkmark size={32} />
			<p>No versions pending approval</p>
			<span class="hint">All submitted versions have been reviewed.</span>
		</div>
	{:else}
		<ul class="approval-list">
			{#each pendingApprovals as item (item.version_id)}
				<li>
					<button
						class="approval-item"
						type="button"
						on:click={() => handleItemClick(item)}
					>
						<div class="item-main">
							<span class="table-name">{item.table_name}</span>
							<Tag type="blue" size="sm">v{item.version_number}</Tag>
						</div>
						<div class="item-meta">
							<span class="submitted-by">by {item.submitted_by_name}</span>
							<span class="submitted-at">
								<Time size={16} />
								{formatRelativeTime(item.submitted_at)}
							</span>
						</div>
						<ChevronRight size={16} class="chevron-icon" />
					</button>
				</li>
			{/each}
		</ul>

		{#if totalCount > MAX_ITEMS}
			<div class="card-footer">
				<Link href="/tables" class="view-all-link">
					View all {totalCount} pending
					<ChevronRight size={16} />
				</Link>
			</div>
		{/if}
	{/if}
</Tile>

<style>
	:global(.pending-approvals-card) {
		min-height: 200px;
		display: flex;
		flex-direction: column;
	}

	.card-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 1rem;
	}

	.card-title {
		font-size: 0.875rem;
		font-weight: 600;
		color: var(--cds-text-primary, #161616);
		margin: 0;
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
		justify-content: center;
		padding: 2rem 1rem;
		text-align: center;
		color: var(--cds-text-secondary, #525252);
		flex: 1;
	}

	.empty-state :global(svg) {
		margin-bottom: 0.5rem;
		color: var(--cds-support-success, #24a148);
	}

	.empty-state p {
		font-size: 0.875rem;
		margin-bottom: 0.25rem;
		color: var(--cds-text-primary, #161616);
	}

	.empty-state .hint {
		font-size: 0.75rem;
		color: var(--cds-text-helper, #6f6f6f);
	}

	.approval-list {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.approval-list li {
		border-bottom: 1px solid var(--cds-border-subtle-01, #e0e0e0);
	}

	.approval-list li:last-child {
		border-bottom: none;
	}

	.approval-item {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		width: 100%;
		padding: 0.75rem 0;
		background: transparent;
		border: none;
		cursor: pointer;
		text-align: left;
		position: relative;
		padding-right: 1.5rem;
		transition: background-color 0.15s ease;
	}

	.approval-item:hover {
		background-color: var(--cds-layer-hover-01, #e8e8e8);
	}

	.approval-item:focus {
		outline: 2px solid var(--cds-focus, #0f62fe);
		outline-offset: -2px;
	}

	.approval-item :global(.chevron-icon) {
		position: absolute;
		right: 0;
		top: 50%;
		transform: translateY(-50%);
		color: var(--cds-icon-secondary, #525252);
	}

	.item-main {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.table-name {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--cds-text-primary, #161616);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 180px;
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		font-size: 0.75rem;
		color: var(--cds-text-secondary, #525252);
	}

	.submitted-by {
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 120px;
	}

	.submitted-at {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		white-space: nowrap;
	}

	.submitted-at :global(svg) {
		color: var(--cds-icon-secondary, #525252);
	}

	.card-footer {
		margin-top: auto;
		padding-top: 0.75rem;
		border-top: 1px solid var(--cds-border-subtle-01, #e0e0e0);
	}

	:global(.view-all-link) {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		font-size: 0.875rem;
	}
</style>
