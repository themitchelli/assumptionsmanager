<script lang="ts">
	import { goto } from '$app/navigation';
	import {
		Button,
		Form,
		TextInput,
		PasswordInput,
		InlineNotification,
		Link,
		Tile,
		ProgressBar
	} from 'carbon-components-svelte';

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';
	let tenantId = '';
	let nameError = '';
	let emailError = '';
	let passwordError = '';
	let confirmPasswordError = '';
	let tenantIdError = '';
	let isSubmitting = false;
	let errorMessage = '';

	// Password strength calculation
	$: passwordStrength = calculatePasswordStrength(password);
	$: strengthLabel = getStrengthLabel(passwordStrength);
	$: strengthStatus = getStrengthStatus(passwordStrength);

	function calculatePasswordStrength(pwd: string): number {
		if (!pwd) return 0;
		let strength = 0;

		// Length checks
		if (pwd.length >= 8) strength += 25;
		if (pwd.length >= 12) strength += 10;

		// Character variety checks
		if (/[a-z]/.test(pwd)) strength += 15;
		if (/[A-Z]/.test(pwd)) strength += 15;
		if (/[0-9]/.test(pwd)) strength += 15;
		if (/[^a-zA-Z0-9]/.test(pwd)) strength += 20;

		return Math.min(strength, 100);
	}

	function getStrengthLabel(strength: number): string {
		if (strength === 0) return '';
		if (strength < 30) return 'Weak';
		if (strength < 60) return 'Fair';
		if (strength < 80) return 'Good';
		return 'Strong';
	}

	function getStrengthStatus(strength: number): 'error' | 'active' | 'finished' {
		if (strength < 30) return 'error';
		if (strength < 80) return 'active';
		return 'finished';
	}

	function validateName(value: string): boolean {
		if (!value.trim()) {
			nameError = 'Name is required';
			return false;
		}
		nameError = '';
		return true;
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

	function validatePassword(value: string): boolean {
		if (!value) {
			passwordError = 'Password is required';
			return false;
		}
		if (value.length < 8) {
			passwordError = 'Password must be at least 8 characters';
			return false;
		}
		passwordError = '';
		return true;
	}

	function validateConfirmPassword(value: string): boolean {
		if (!value) {
			confirmPasswordError = 'Please confirm your password';
			return false;
		}
		if (value !== password) {
			confirmPasswordError = 'Passwords do not match';
			return false;
		}
		confirmPasswordError = '';
		return true;
	}

	function validateTenantId(value: string): boolean {
		if (!value.trim()) {
			tenantIdError = 'Tenant code is required';
			return false;
		}
		// UUID format validation
		const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
		if (!uuidRegex.test(value.trim())) {
			tenantIdError = 'Please enter a valid tenant code';
			return false;
		}
		tenantIdError = '';
		return true;
	}

	function handleNameBlur() {
		if (name) validateName(name);
	}

	function handleEmailBlur() {
		if (email) validateEmail(email);
	}

	function handlePasswordBlur() {
		if (password) validatePassword(password);
	}

	function handleConfirmPasswordBlur() {
		if (confirmPassword) validateConfirmPassword(confirmPassword);
	}

	function handleTenantIdBlur() {
		if (tenantId) validateTenantId(tenantId);
	}

	async function handleSubmit() {
		// Clear previous errors
		errorMessage = '';

		// Validate all fields before submission
		const isNameValid = validateName(name);
		const isEmailValid = validateEmail(email);
		const isPasswordValid = validatePassword(password);
		const isConfirmPasswordValid = validateConfirmPassword(confirmPassword);
		const isTenantIdValid = validateTenantId(tenantId);

		if (!isNameValid || !isEmailValid || !isPasswordValid || !isConfirmPasswordValid || !isTenantIdValid) {
			return;
		}

		isSubmitting = true;

		try {
			const response = await fetch('/api/auth/register', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					email,
					password,
					tenant_id: tenantId.trim()
				})
			});

			if (!response.ok) {
				const data = await response.json();
				if (response.status === 409) {
					errorMessage = 'This email is already registered for this tenant';
				} else if (response.status === 404) {
					errorMessage = 'Tenant not found. Please check your tenant code';
				} else {
					errorMessage = data.detail || 'Registration failed. Please try again.';
				}
				return;
			}

			// Registration successful - redirect to login with success message
			goto('/login?registered=true');
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
	<title>Register | Assumptions Manager</title>
</svelte:head>

<div class="register-container">
	<Tile class="register-tile">
		<h1>Assumptions Manager</h1>
		<h2>Create your account</h2>

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
					id="name"
					labelText="Name"
					placeholder="Enter your full name"
					bind:value={name}
					invalid={!!nameError}
					invalidText={nameError}
					on:blur={handleNameBlur}
					on:keydown={handleKeydown}
					required
				/>
			</div>

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
					placeholder="Create a password"
					bind:value={password}
					invalid={!!passwordError}
					invalidText={passwordError}
					on:blur={handlePasswordBlur}
					on:keydown={handleKeydown}
					required
				/>
				{#if password}
					<div class="password-strength">
						<ProgressBar
							value={passwordStrength}
							max={100}
							size="sm"
							status={strengthStatus}
							hideLabel
						/>
						<span class="strength-label" class:weak={passwordStrength < 30} class:fair={passwordStrength >= 30 && passwordStrength < 60} class:good={passwordStrength >= 60 && passwordStrength < 80} class:strong={passwordStrength >= 80}>
							{strengthLabel}
						</span>
					</div>
				{/if}
			</div>

			<div class="form-field">
				<PasswordInput
					id="confirmPassword"
					labelText="Confirm password"
					placeholder="Confirm your password"
					bind:value={confirmPassword}
					invalid={!!confirmPasswordError}
					invalidText={confirmPasswordError}
					on:blur={handleConfirmPasswordBlur}
					on:keydown={handleKeydown}
					required
				/>
			</div>

			<div class="form-field">
				<TextInput
					id="tenantId"
					labelText="Tenant code"
					placeholder="Enter your organisation's tenant code"
					helperText="Contact your administrator if you don't have a tenant code"
					bind:value={tenantId}
					invalid={!!tenantIdError}
					invalidText={tenantIdError}
					on:blur={handleTenantIdBlur}
					on:keydown={handleKeydown}
					required
				/>
			</div>

			<Button type="submit" disabled={isSubmitting} class="submit-button">
				{#if isSubmitting}
					Creating account...
				{:else}
					Create account
				{/if}
			</Button>
		</Form>

		<div class="login-link">
			<span>Already have an account?</span>
			<Link href="/login">Sign in</Link>
		</div>
	</Tile>
</div>

<style>
	.register-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 100vh;
		background-color: var(--cds-ui-background, #f4f4f4);
		padding: 1rem;
	}

	.register-container :global(.register-tile) {
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

	.password-strength {
		margin-top: 0.5rem;
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.password-strength :global(.bx--progress-bar) {
		flex: 1;
	}

	.strength-label {
		font-size: 0.75rem;
		font-weight: 500;
		min-width: 3rem;
	}

	.strength-label.weak {
		color: var(--cds-support-error, #da1e28);
	}

	.strength-label.fair {
		color: var(--cds-support-warning, #f1c21b);
	}

	.strength-label.good {
		color: var(--cds-support-success, #24a148);
	}

	.strength-label.strong {
		color: var(--cds-support-success, #24a148);
	}

	.register-container :global(.submit-button) {
		width: 100%;
		margin-top: 1rem;
	}

	.login-link {
		margin-top: 1.5rem;
		text-align: center;
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
	}

	.login-link span {
		margin-right: 0.25rem;
	}
</style>
