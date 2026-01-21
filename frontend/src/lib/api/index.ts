/**
 * API client module
 *
 * Centralised API client with automatic authentication and error handling.
 */

export { api, getAuthToken } from './client';
export type { ApiError, ApiResponse } from './client';
export * from './types';
