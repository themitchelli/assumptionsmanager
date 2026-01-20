import { writable } from 'svelte/store';

export type ToastKind = 'error' | 'info' | 'info-square' | 'success' | 'warning' | 'warning-alt';

export interface Toast {
	id: string;
	kind: ToastKind;
	title: string;
	subtitle?: string;
	timeout?: number;
}

function createToastStore() {
	const { subscribe, update } = writable<Toast[]>([]);

	return {
		subscribe,
		add: (toast: Omit<Toast, 'id'>) => {
			const id = crypto.randomUUID();
			const newToast: Toast = { ...toast, id };
			update((toasts) => [...toasts, newToast]);

			// Auto-remove after timeout (default 5 seconds)
			const timeout = toast.timeout ?? 5000;
			if (timeout > 0) {
				setTimeout(() => {
					update((toasts) => toasts.filter((t) => t.id !== id));
				}, timeout);
			}

			return id;
		},
		remove: (id: string) => {
			update((toasts) => toasts.filter((t) => t.id !== id));
		},
		clear: () => {
			update(() => []);
		},
		// Convenience methods
		error: (title: string, subtitle?: string) => {
			return createToastStore().add({ kind: 'error', title, subtitle });
		},
		success: (title: string, subtitle?: string) => {
			return createToastStore().add({ kind: 'success', title, subtitle });
		},
		warning: (title: string, subtitle?: string) => {
			return createToastStore().add({ kind: 'warning', title, subtitle });
		},
		info: (title: string, subtitle?: string) => {
			return createToastStore().add({ kind: 'info', title, subtitle });
		}
	};
}

export const toasts = createToastStore();
