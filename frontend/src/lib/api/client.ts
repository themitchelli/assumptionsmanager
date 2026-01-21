/**
 * Centralized API client with automatic authentication and error handling.
 *
 * Features:
 * - Automatically attaches Authorization header when authenticated
 * - Handles 401 responses by logging out and redirecting to /login
 * - Consistent error handling for network errors, 4xx, and 5xx
 * - TypeScript interfaces for type safety
 * - Request/response logging in development mode
 */

import { browser } from '$app/environment';
import { goto } from '$app/navigation';
import { auth } from '$lib/stores/auth';

/**
 * Base URL configurable via environment variable (PUBLIC_API_BASE_URL)
 * Falls back to '/api' for development with Vite proxy
 *
 * Set in .env file:
 *   PUBLIC_API_BASE_URL=https://api.example.com
 *
 * Or leave unset to use default '/api' (proxied by Vite in dev)
 */
function getApiBaseUrl(): string {
	// Try to get from environment (works in both dev and production)
	try {
		// Dynamic import to handle missing env var gracefully
		const envUrl = import.meta.env.PUBLIC_API_BASE_URL;
		if (envUrl) return envUrl;
	} catch {
		// Env var not defined, use default
	}
	return '/api';
}

const API_BASE_URL = getApiBaseUrl();

export interface ApiError {
	status: number;
	message: string;
	detail?: string;
}

export interface ApiResponse<T> {
	data?: T;
	error?: ApiError;
}

/**
 * Log request/response in development mode
 */
function logRequest(method: string, url: string, options?: RequestInit) {
	if (import.meta.env.DEV) {
		console.log(`[API] ${method} ${url}`, options?.body ? JSON.parse(options.body as string) : '');
	}
}

function logResponse(method: string, url: string, status: number, data: unknown) {
	if (import.meta.env.DEV) {
		console.log(`[API] ${method} ${url} -> ${status}`, data);
	}
}

function logError(method: string, url: string, error: ApiError) {
	if (import.meta.env.DEV) {
		console.error(`[API] ${method} ${url} -> ERROR`, error);
	}
}

/**
 * Get the current auth token from sessionStorage
 */
export function getAuthToken(): string | null {
	if (browser) {
		return sessionStorage.getItem('auth_token');
	}
	return null;
}

/**
 * Handle 401 responses by logging out and redirecting to login
 */
async function handleUnauthorized() {
	if (browser) {
		auth.logout();
		const returnUrl = encodeURIComponent(window.location.pathname);
		await goto(`/login?returnUrl=${returnUrl}`);
	}
}

/**
 * Parse error response from API
 */
async function parseErrorResponse(response: Response): Promise<ApiError> {
	try {
		const data = await response.json();
		// Handle FastAPI validation errors (detail is an array of error objects)
		// Handle FastAPI error strings (detail is a string)
		// Handle generic error objects (message field)
		let message: string;
		if (typeof data.detail === 'string') {
			message = data.detail;
		} else if (Array.isArray(data.detail)) {
			// FastAPI validation error format: [{msg: string, loc: string[], ...}]
			message = data.detail.map((e: { msg?: string }) => e.msg || 'Validation error').join(', ');
		} else if (typeof data.message === 'string') {
			message = data.message;
		} else {
			message = response.statusText || 'An error occurred';
		}
		return {
			status: response.status,
			message,
			detail: typeof data.detail === 'string' ? data.detail : undefined
		};
	} catch {
		return {
			status: response.status,
			message: response.statusText || 'An error occurred'
		};
	}
}

/**
 * Make an authenticated API request
 */
async function request<T>(
	method: string,
	endpoint: string,
	options: {
		body?: unknown;
		headers?: Record<string, string>;
		skipAuth?: boolean;
	} = {}
): Promise<ApiResponse<T>> {
	const url = `${API_BASE_URL}${endpoint}`;
	const token = getAuthToken();

	const headers: Record<string, string> = {
		...options.headers
	};

	// Add Content-Type for requests with body
	if (options.body && !headers['Content-Type']) {
		headers['Content-Type'] = 'application/json';
	}

	// Add Authorization header if authenticated and not explicitly skipped
	if (token && !options.skipAuth) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const requestOptions: RequestInit = {
		method,
		headers
	};

	if (options.body) {
		requestOptions.body = JSON.stringify(options.body);
	}

	logRequest(method, url, requestOptions);

	try {
		const response = await fetch(url, requestOptions);

		// Handle 401 Unauthorized - logout and redirect
		if (response.status === 401 && !options.skipAuth) {
			const error: ApiError = {
				status: 401,
				message: 'Session expired. Please sign in again.'
			};
			logError(method, url, error);
			await handleUnauthorized();
			return { error };
		}

		// Handle error responses
		if (!response.ok) {
			const error = await parseErrorResponse(response);
			logError(method, url, error);
			return { error };
		}

		// Handle 204 No Content
		if (response.status === 204) {
			logResponse(method, url, response.status, null);
			return { data: undefined as T };
		}

		// Parse JSON response
		const data = await response.json();
		logResponse(method, url, response.status, data);
		return { data };
	} catch (error) {
		// Network error
		const apiError: ApiError = {
			status: 0,
			message: 'Network error. Please check your connection.'
		};
		logError(method, url, apiError);
		return { error: apiError };
	}
}

/**
 * Make a multipart/form-data request (for file uploads)
 */
async function requestFormData<T>(
	method: string,
	endpoint: string,
	formData: FormData
): Promise<ApiResponse<T>> {
	const url = `${API_BASE_URL}${endpoint}`;
	const token = getAuthToken();

	const headers: Record<string, string> = {};

	// Add Authorization header if authenticated
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	// Note: Don't set Content-Type for FormData - browser sets it with boundary

	logRequest(method, url);

	try {
		const response = await fetch(url, {
			method,
			headers,
			body: formData
		});

		// Handle 401 Unauthorized
		if (response.status === 401) {
			const error: ApiError = {
				status: 401,
				message: 'Session expired. Please sign in again.'
			};
			logError(method, url, error);
			await handleUnauthorized();
			return { error };
		}

		// Handle error responses
		if (!response.ok) {
			const error = await parseErrorResponse(response);
			logError(method, url, error);
			return { error };
		}

		// Parse JSON response
		const data = await response.json();
		logResponse(method, url, response.status, data);
		return { data };
	} catch (error) {
		const apiError: ApiError = {
			status: 0,
			message: 'Network error. Please check your connection.'
		};
		logError(method, url, apiError);
		return { error: apiError };
	}
}

// Convenience methods
export const api = {
	get: <T>(endpoint: string, options?: { skipAuth?: boolean }) =>
		request<T>('GET', endpoint, options),

	post: <T>(endpoint: string, body?: unknown, options?: { skipAuth?: boolean }) =>
		request<T>('POST', endpoint, { body, ...options }),

	put: <T>(endpoint: string, body?: unknown) => request<T>('PUT', endpoint, { body }),

	patch: <T>(endpoint: string, body?: unknown) => request<T>('PATCH', endpoint, { body }),

	delete: <T>(endpoint: string) => request<T>('DELETE', endpoint),

	/**
	 * Upload a file using multipart/form-data
	 */
	upload: <T>(endpoint: string, formData: FormData) =>
		requestFormData<T>('POST', endpoint, formData)
};
