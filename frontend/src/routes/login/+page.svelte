<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import {
		Button,
		Form,
		TextInput,
		PasswordInput,
		InlineNotification,
		Link,
		Tile
	} from 'carbon-components-svelte';
	import { auth } from '$lib/stores/auth';

	let email = '';
	let password = '';
	let emailError = '';
	let isSubmitting = false;
	let errorMessage = '';
	let successMessage = '';

	// Get the return URL from query params if present
	$: returnUrl = $page.url.searchParams.get('returnUrl') || '/dashboard';

	// Check if user just registered
	$: if ($page.url.searchParams.get('registered') === 'true') {
		successMessage = 'Account created successfully. Please sign in.';
	}

	function validateEmail(value: string): boolean {
		if (!value) {
			emailError = 'Email is required';
			return false;
		}
		const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		if (!emailRegex.test(value)) {
			emailError = 'Please enter a valid email address';
			return false;
		}
		emailError = '';
		return true;
	}

	function handleEmailBlur() {
		if (email) {
			validateEmail(email);
		}
	}

	async function handleSubmit() {
		// Clear previous errors
		errorMessage = '';

		// Validate email format before submission
		if (!validateEmail(email)) {
			return;
		}

		if (!password) {
			errorMessage = 'Password is required';
			return;
		}

		isSubmitting = true;

		try {
			const response = await fetch('/api/auth/login', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ email, password })
			});

			if (!response.ok) {
				const data = await response.json();
				if (response.status === 401) {
					errorMessage = 'Invalid email or password';
				} else {
					errorMessage = data.detail || 'Login failed. Please try again.';
				}
				return;
			}

			const data = await response.json();

			// Store the token securely in sessionStorage (not localStorage per security requirements)
			sessionStorage.setItem('auth_token', data.access_token);

			// Fetch user info to populate the auth store
			const userResponse = await fetch('/api/auth/me', {
				headers: {
					Authorization: `Bearer ${data.access_token}`
				}
			});

			if (userResponse.ok) {
				const user = await userResponse.json();
				auth.setUser(
					{
						id: user.id,
						email: user.email,
						name: user.email.split('@')[0], // Use email prefix as name for now
						role: user.role,
						tenant_id: user.tenant_id
					},
					data.access_token
				);
			}

			// Redirect to the return URL or dashboard
			goto(returnUrl);
		} catch (err) {
			errorMessage = 'Network error. Please check your connection and try again.';
		} finally {
			isSubmitting = false;
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter' && !isSubmitting) {
			handleSubmit();
		}
	}
</script>

<svelte:head>
	<title>Login | Assumptions Manager</title>
</svelte:head>

<div class="login-container">
	<Tile class="login-tile">
		<h1>Assumptions Manager</h1>
		<h2>Sign in to your account</h2>

		{#if successMessage}
			<InlineNotification
				lowContrast
				kind="success"
				title="Success"
				subtitle={successMessage}
				on:close={() => (successMessage = '')}
			/>
		{/if}

		{#if errorMessage}
			<InlineNotification
				lowContrast
				kind="error"
				title="Error"
				subtitle={errorMessage}
				on:close={() => (errorMessage = '')}
			/>
		{/if}

		<Form on:submit={handleSubmit}>
			<div class="form-field">
				<TextInput
					id="email"
					labelText="Email"
					placeholder="Enter your email"
					type="email"
					bind:value={email}
					invalid={!!emailError}
					invalidText={emailError}
					on:blur={handleEmailBlur}
					on:keydown={handleKeydown}
					required
				/>
			</div>

			<div class="form-field">
				<PasswordInput
					id="password"
					labelText="Password"
					placeholder="Enter your password"
					bind:value={password}
					on:keydown={handleKeydown}
					required
				/>
			</div>

			<Button type="submit" disabled={isSubmitting} class="submit-button">
				{#if isSubmitting}
					Signing in...
				{:else}
					Sign in
				{/if}
			</Button>
		</Form>

		<div class="register-link">
			<span>Don't have an account?</span>
			<Link href="/register">Create one</Link>
		</div>
	</Tile>
</div>

<style>
	.login-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 100vh;
		background-color: var(--cds-ui-background, #f4f4f4);
		padding: 1rem;
	}

	.login-container :global(.login-tile) {
		width: 100%;
		max-width: 400px;
		padding: 2rem;
	}

	h1 {
		font-size: 1.75rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		color: var(--cds-text-primary, #161616);
	}

	h2 {
		font-size: 1rem;
		font-weight: 400;
		margin-bottom: 1.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	.form-field {
		margin-bottom: 1rem;
	}

	.login-container :global(.submit-button) {
		width: 100%;
		margin-top: 1rem;
	}

	.register-link {
		margin-top: 1.5rem;
		text-align: center;
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
	}

	.register-link span {
		margin-right: 0.25rem;
	}
</style>
