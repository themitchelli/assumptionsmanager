import { writable } from 'svelte/store';

export interface Breadcrumb {
	label: string;
	href?: string;
}

function createBreadcrumbStore() {
	const { subscribe, set } = writable<Breadcrumb[]>([]);

	return {
		subscribe,
		set: (breadcrumbs: Breadcrumb[]) => set(breadcrumbs),
		clear: () => set([])
	};
}

export const breadcrumbs = createBreadcrumbStore();

export const isNavigating = writable(false);
