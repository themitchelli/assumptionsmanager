import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

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

const AUTH_TOKEN_KEY = 'auth_token';
const AUTH_USER_KEY = 'auth_user';

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
			// Store in sessionStorage (never localStorage per security requirements)
			if (browser) {
				sessionStorage.setItem(AUTH_TOKEN_KEY, token);
				sessionStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
			}
			update((state) => ({
				...state,
				user,
				token,
				isAuthenticated: true,
				isLoading: false
			}));
		},
		logout: () => {
			// Clear all auth state from sessionStorage
			if (browser) {
				sessionStorage.removeItem(AUTH_TOKEN_KEY);
				sessionStorage.removeItem(AUTH_USER_KEY);
			}
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
		},
		/**
		 * Initialize auth state from sessionStorage.
		 * Called on app startup to restore session after page refresh.
		 */
		initialize: async () => {
			if (!browser) {
				update((state) => ({ ...state, isLoading: false }));
				return;
			}

			const token = sessionStorage.getItem(AUTH_TOKEN_KEY);
			const userJson = sessionStorage.getItem(AUTH_USER_KEY);

			if (!token || !userJson) {
				update((state) => ({ ...state, isLoading: false }));
				return;
			}

			try {
				const user = JSON.parse(userJson) as User;
				// Validate token by calling /auth/me
				const response = await fetch('/api/auth/me', {
					headers: {
						Authorization: `Bearer ${token}`
					}
				});

				if (response.ok) {
					const freshUser = await response.json();
					update((state) => ({
						...state,
						user: {
							id: freshUser.id,
							email: freshUser.email,
							name: freshUser.name || freshUser.email.split('@')[0],
							role: freshUser.role,
							tenant_id: freshUser.tenant_id,
							tenant_name: user.tenant_name
						},
						token,
						isAuthenticated: true,
						isLoading: false
					}));
				} else {
					// Token is invalid or expired - clear auth state
					sessionStorage.removeItem(AUTH_TOKEN_KEY);
					sessionStorage.removeItem(AUTH_USER_KEY);
					update((state) => ({ ...state, isLoading: false }));
				}
			} catch {
				// Network error or invalid JSON - clear auth state
				sessionStorage.removeItem(AUTH_TOKEN_KEY);
				sessionStorage.removeItem(AUTH_USER_KEY);
				update((state) => ({ ...state, isLoading: false }));
			}
		},
		/**
		 * Get the current token synchronously (for use in API client)
		 */
		getToken: (): string | null => {
			if (browser) {
				return sessionStorage.getItem(AUTH_TOKEN_KEY);
			}
			return null;
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
