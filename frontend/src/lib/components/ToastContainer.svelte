<script lang="ts">
	import { ToastNotification } from 'carbon-components-svelte';
	import { toasts } from '$lib/stores/toast';
</script>

{#if $toasts.length > 0}
	<div class="toast-container">
		{#each $toasts as toast (toast.id)}
			<ToastNotification
				kind={toast.kind}
				title={toast.title}
				subtitle={toast.subtitle}
				lowContrast
				on:close={() => toasts.remove(toast.id)}
			/>
		{/each}
	</div>
{/if}

<style>
	.toast-container {
		position: fixed;
		top: 3.5rem;
		right: 1rem;
		z-index: 9999;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-width: 400px;
	}
</style>
