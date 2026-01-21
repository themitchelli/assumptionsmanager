<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		Tile,
		FileUploader,
		TextInput,
		TextArea,
		Button,
		InlineNotification,
		InlineLoading,
		DataTable,
		Tag
	} from 'carbon-components-svelte';
	import { Upload, ArrowLeft, DocumentImport } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { toasts } from '$lib/stores/toast';
	import { getAuthToken } from '$lib/api';
	import type { ImportPreviewResponse, ImportResponse } from '$lib/api/types';

	// Form state
	let tableName = '';
	let description = '';
	let files: File[] = [];

	// Preview state
	let preview: ImportPreviewResponse | null = null;
	let loadingPreview = false;
	let previewError: string | null = null;

	// Import state
	let importing = false;
	let importError: string | null = null;

	// Permission check
	$: canImport = $auth.user?.role === 'analyst' || $auth.user?.role === 'admin' || $auth.user?.role === 'super_admin';

	// Validation
	$: isFormValid = tableName.trim() !== '' && files.length > 0 && preview && preview.errors.length === 0;

	async function handleFileChange(event: CustomEvent<readonly File[]>) {
		files = [...event.detail];
		preview = null;
		previewError = null;

		if (files.length > 0) {
			await loadPreview();
		}
	}

	async function loadPreview() {
		if (files.length === 0) return;

		loadingPreview = true;
		previewError = null;

		const formData = new FormData();
		formData.append('file', files[0]);

		try {
			const token = getAuthToken();
			const response = await fetch('/api/tables/import/csv/preview', {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${token}`
				},
				body: formData
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
				previewError = errorData.detail || `HTTP ${response.status}`;
				preview = null;
			} else {
				preview = await response.json();
			}
		} catch (err) {
			previewError = err instanceof Error ? err.message : 'Network error';
			preview = null;
		} finally {
			loadingPreview = false;
		}
	}

	async function handleImport() {
		if (!isFormValid || !preview) return;

		importing = true;
		importError = null;

		const formData = new FormData();
		formData.append('file', files[0]);
		formData.append('table_name', tableName.trim());
		if (description.trim()) {
			formData.append('description', description.trim());
		}

		try {
			const token = getAuthToken();
			const response = await fetch('/api/tables/import/csv', {
				method: 'POST',
				headers: {
					'Authorization': `Bearer ${token}`
				},
				body: formData
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({ detail: 'Import failed' }));
				importError = errorData.detail || `HTTP ${response.status}`;
			} else {
				const result: ImportResponse = await response.json();
				toasts.success('Import successful', `Created table "${result.table_name}" with ${result.row_count} rows.`);
				goto(`/tables/${result.table_id}`);
			}
		} catch (err) {
			importError = err instanceof Error ? err.message : 'Network error';
		} finally {
			importing = false;
		}
	}

	function handleClearFile() {
		files = [];
		preview = null;
		previewError = null;
	}

	function getTypeTagColor(type: string): 'blue' | 'cyan' | 'purple' | 'teal' | 'green' {
		switch (type) {
			case 'integer': return 'blue';
			case 'decimal': return 'cyan';
			case 'date': return 'purple';
			case 'boolean': return 'teal';
			default: return 'green';
		}
	}

	function getTypeAbbreviation(type: string): string {
		switch (type) {
			case 'integer': return 'INT';
			case 'decimal': return 'DEC';
			case 'date': return 'DATE';
			case 'boolean': return 'BOOL';
			default: return 'TEXT';
		}
	}

	onMount(() => {
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: 'Import CSV' }
		]);
	});
</script>

<svelte:head>
	<title>Import CSV - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<Button
				kind="ghost"
				icon={ArrowLeft}
				href="/tables"
				class="back-button"
			>
				Back to Tables
			</Button>
		</Column>
	</Row>

	<Row>
		<Column>
			<h1 class="page-title">Import CSV</h1>
			<p class="page-description">Upload a CSV file to create a new assumption table</p>
		</Column>
	</Row>

	{#if !canImport}
		<Row>
			<Column>
				<InlineNotification
					kind="warning"
					title="Permission denied"
					subtitle="Only analysts and admins can import tables."
					hideCloseButton
				/>
			</Column>
		</Row>
	{:else}
		<Row>
			<Column lg={8} md={6} sm={4}>
				<Tile class="upload-section">
					<h3 class="section-title">1. Upload CSV File</h3>

					<FileUploader
						labelTitle="Select file"
						labelDescription="Max file size is 10MB. Supported formats: .csv"
						buttonLabel="Add file"
						accept={['.csv']}
						status={loadingPreview ? 'uploading' : 'complete'}
						on:change={handleFileChange}
						on:remove={handleClearFile}
					/>

					{#if loadingPreview}
						<div class="loading-container">
							<InlineLoading description="Analyzing file..." />
						</div>
					{/if}

					{#if previewError}
						<InlineNotification
							kind="error"
							title="Preview failed"
							subtitle={previewError}
							lowContrast
						/>
					{/if}
				</Tile>

				{#if preview}
					<Tile class="preview-section">
						<h3 class="section-title">2. Preview</h3>

						{#if preview.errors.length > 0}
							<InlineNotification
								kind="error"
								title="Validation errors"
								subtitle="{preview.errors.length} error(s) found in the CSV file"
								lowContrast
								hideCloseButton
							/>

							<div class="error-list">
								{#each preview.errors.slice(0, 10) as error}
									<div class="error-item">
										<strong>Row {error.row}, Column "{error.column}":</strong>
										{error.message}
									</div>
								{/each}
								{#if preview.errors.length > 10}
									<p class="more-errors">... and {preview.errors.length - 10} more errors</p>
								{/if}
							</div>
						{:else}
							<div class="preview-stats">
								<span class="stat"><strong>{preview.columns.length}</strong> columns detected</span>
								<span class="stat"><strong>{preview.row_count}</strong> rows detected</span>
							</div>

							<div class="columns-preview">
								<h4>Detected Columns</h4>
								<div class="column-tags">
									{#each preview.columns as col}
										<div class="column-tag">
											<span class="column-name">{col.name}</span>
											<Tag type={getTypeTagColor(col.inferred_type)} size="sm">
												{getTypeAbbreviation(col.inferred_type)}
											</Tag>
										</div>
									{/each}
								</div>
							</div>
						{/if}
					</Tile>

					{#if preview.errors.length === 0}
						<Tile class="form-section">
							<h3 class="section-title">3. Table Details</h3>

							<TextInput
								bind:value={tableName}
								labelText="Table name"
								placeholder="Enter table name"
								required
								invalid={tableName.trim() === ''}
								invalidText="Table name is required"
							/>

							<TextArea
								bind:value={description}
								labelText="Description (optional)"
								placeholder="Enter a description for this table"
								rows={3}
							/>

							{#if importError}
								<InlineNotification
									kind="error"
									title="Import failed"
									subtitle={importError}
									lowContrast
									on:close={() => (importError = null)}
								/>
							{/if}

							<div class="form-actions">
								<Button
									kind="primary"
									icon={DocumentImport}
									on:click={handleImport}
									disabled={!isFormValid || importing}
								>
									{#if importing}
										<InlineLoading description="Importing..." />
									{:else}
										Import Table
									{/if}
								</Button>
								<Button kind="secondary" href="/tables">Cancel</Button>
							</div>
						</Tile>
					{/if}
				{/if}
			</Column>

			<Column lg={4} md={2} sm={4}>
				<Tile class="help-section">
					<h4>CSV Format Requirements</h4>
					<ul class="help-list">
						<li>First row must contain column headers</li>
						<li>Columns are comma-separated</li>
						<li>Use UTF-8 encoding</li>
						<li>Maximum file size: 10MB</li>
					</ul>

					<h4>Supported Data Types</h4>
					<ul class="help-list">
						<li><Tag type="green" size="sm">TEXT</Tag> Any text value</li>
						<li><Tag type="blue" size="sm">INT</Tag> Whole numbers</li>
						<li><Tag type="cyan" size="sm">DEC</Tag> Decimal numbers</li>
						<li><Tag type="purple" size="sm">DATE</Tag> YYYY-MM-DD format</li>
						<li><Tag type="teal" size="sm">BOOL</Tag> true/false, yes/no, 1/0</li>
					</ul>
				</Tile>
			</Column>
		</Row>
	{/if}
</Grid>

<style>
	.page-title {
		margin-bottom: 0.5rem;
		font-size: 2rem;
		font-weight: 400;
	}

	.page-description {
		margin-bottom: 1.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	:global(.back-button) {
		margin-bottom: 1rem;
	}

	.section-title {
		font-size: 1rem;
		font-weight: 600;
		margin-bottom: 1rem;
	}

	:global(.upload-section),
	:global(.preview-section),
	:global(.form-section),
	:global(.help-section) {
		margin-bottom: 1rem;
	}

	.loading-container {
		margin-top: 1rem;
	}

	.preview-stats {
		display: flex;
		gap: 2rem;
		margin-bottom: 1rem;
	}

	.stat {
		color: var(--cds-text-secondary, #525252);
	}

	.columns-preview h4 {
		font-size: 0.875rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
	}

	.column-tags {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.column-tag {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		background: var(--cds-layer-02, #e0e0e0);
		padding: 0.25rem 0.5rem;
		border-radius: 4px;
	}

	.column-name {
		font-size: 0.875rem;
		font-weight: 500;
	}

	.error-list {
		margin-top: 1rem;
	}

	.error-item {
		padding: 0.5rem;
		margin-bottom: 0.5rem;
		background: var(--cds-notification-error-background, #fff1f1);
		border-left: 3px solid var(--cds-support-error, #da1e28);
		font-size: 0.875rem;
	}

	.more-errors {
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
		font-style: italic;
	}

	.form-actions {
		display: flex;
		gap: 1rem;
		margin-top: 1.5rem;
	}

	:global(.help-section h4) {
		font-size: 0.875rem;
		font-weight: 600;
		margin-bottom: 0.5rem;
		margin-top: 1rem;
	}

	:global(.help-section h4:first-child) {
		margin-top: 0;
	}

	.help-list {
		margin: 0;
		padding-left: 1.25rem;
		font-size: 0.875rem;
		color: var(--cds-text-secondary, #525252);
	}

	.help-list li {
		margin-bottom: 0.25rem;
	}

	:global(.help-section .bx--tag) {
		vertical-align: middle;
	}
</style>
