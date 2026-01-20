import { writable, derived } from 'svelte/store';

export interface User {
	id: string;
	email: string;
	name?: string;
	role: 'viewer' | 'analyst' | 'admin' | 'super_admin';
	tenant_id: string;
	tenant_name?: string;
}

interface AuthState {
	user: User | null;
	token: string | null;
	isAuthenticated: boolean;
	isLoading: boolean;
}

const initialState: AuthState = {
	user: null,
	token: null,
	isAuthenticated: false,
	isLoading: true
};

function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>(initialState);

	return {
		subscribe,
		setUser: (user: User, token: string) => {
			update((state) => ({
				...state,
				user,
				token,
				isAuthenticated: true,
				isLoading: false
			}));
		},
		logout: () => {
			set({
				user: null,
				token: null,
				isAuthenticated: false,
				isLoading: false
			});
		},
		setLoading: (isLoading: boolean) => {
			update((state) => ({ ...state, isLoading }));
		},
		finishLoading: () => {
			update((state) => ({ ...state, isLoading: false }));
		}
	};
}

export const auth = createAuthStore();

export const isAdmin = derived(auth, ($auth) => {
	return $auth.user?.role === 'admin' || $auth.user?.role === 'super_admin';
});

export const isSuperAdmin = derived(auth, ($auth) => {
	return $auth.user?.role === 'super_admin';
});

export const userRole = derived(auth, ($auth) => $auth.user?.role ?? null);
