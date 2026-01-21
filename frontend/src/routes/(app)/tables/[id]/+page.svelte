<script lang="ts">
	import { page } from '$app/stores';
	import { onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import {
		Grid,
		Row,
		Column,
		Tile,
		Tag,
		Button,
		SkeletonText,
		SkeletonPlaceholder,
		ToastNotification,
		Checkbox
	} from 'carbon-components-svelte';
	import { ArrowLeft, Calendar, Time, Add, RowInsert, TrashCan, RecentlyViewed } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { toasts } from '$lib/stores/toast';
	import { api } from '$lib/api';
	import type { TableDetailResponse, ColumnResponse, RowResponse, CellData } from '$lib/api/types';
	import AddColumnModal from '$lib/components/AddColumnModal.svelte';
	import AddMultipleRowsModal from '$lib/components/AddMultipleRowsModal.svelte';
	import DeleteRowsModal from '$lib/components/DeleteRowsModal.svelte';
	import DeleteTableModal from '$lib/components/DeleteTableModal.svelte';

	// Get table ID from route
	$: tableId = $page.params.id;

	// State
	let table: TableDetailResponse | null = null;
	let loading = true;
	let error: string | null = null;

	// Modal state
	let showAddColumnModal = false;
	let showAddMultipleRowsModal = false;
	let showDeleteRowsModal = false;
	let showDeleteTableModal = false;

	// Row creation state
	let addingRow = false;

	// Row selection state
	let selectedRowIds: Set<string> = new Set();
	$: selectedRowCount = selectedRowIds.size;
	$: allRowsSelected = table !== null && table.rows.length > 0 && selectedRowIds.size === table.rows.length;
	$: someRowsSelected = selectedRowIds.size > 0 && !allRowsSelected;

	// Inline editing state
	let editingCell: { rowId: string; columnName: string } | null = null;
	let editValue: string | number | boolean | null = null;
	let editBoolValue = false; // Separate boolean for Checkbox binding
	let originalValue: string | number | boolean | null = null;
	let savingCell = false;
	let cellInputRef: HTMLInputElement | null = null;

	// Role-based permissions
	$: canEdit = $auth.user?.role === 'analyst' || $auth.user?.role === 'admin' || $auth.user?.role === 'super_admin';
	$: canDelete = $auth.user?.role === 'admin' || $auth.user?.role === 'super_admin';

	// Get existing column names for validation
	$: existingColumnNames = table?.columns.map((c) => c.name) || [];

	// Row selection functions
	function toggleRowSelection(rowId: string) {
		if (selectedRowIds.has(rowId)) {
			selectedRowIds.delete(rowId);
		} else {
			selectedRowIds.add(rowId);
		}
		selectedRowIds = selectedRowIds; // Trigger reactivity
	}

	function toggleAllRows() {
		if (!table) return;
		if (allRowsSelected) {
			// Deselect all
			selectedRowIds = new Set();
		} else {
			// Select all
			selectedRowIds = new Set(table.rows.map((r) => r.id));
		}
	}

	function clearSelection() {
		selectedRowIds = new Set();
	}

	// Get selected rows for delete modal
	$: selectedRows = table?.rows.filter((r) => selectedRowIds.has(r.id)) || [];

	// Handle delete rows modal
	function handleOpenDeleteRowsModal() {
		if (selectedRowCount === 0) return;
		showDeleteRowsModal = true;
	}

	async function handleRowsDeleted(event: CustomEvent<string[]>) {
		const deletedIds = event.detail;
		if (table) {
			// Remove deleted rows from table
			table = {
				...table,
				rows: table.rows.filter((r) => !deletedIds.includes(r.id))
			};
		}
		// Clear selection
		clearSelection();
		showDeleteRowsModal = false;
		toasts.success(
			'Rows deleted',
			`${deletedIds.length} row${deletedIds.length !== 1 ? 's' : ''} deleted successfully`
		);
	}

	// Handle table deletion
	function handleTableDeleted() {
		showDeleteTableModal = false;
		toasts.success('Table deleted', `Table "${table?.name}" has been deleted`);
		goto('/tables');
	}

	// Fetch table data
	async function fetchTable() {
		loading = true;
		error = null;
		const response = await api.get<TableDetailResponse>(`/tables/${tableId}`);
		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			table = response.data;
			// Update breadcrumbs with actual table name
			breadcrumbs.set([
				{ label: 'Tables', href: '/tables' },
				{ label: table.name }
			]);
		}
		loading = false;
	}

	// Format date for display
	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	// Format datetime for display
	function formatDateTime(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Get data type tag color
	function getDataTypeTag(dataType: string): { text: string; type: 'blue' | 'green' | 'purple' | 'cyan' | 'teal' } {
		switch (dataType) {
			case 'integer':
				return { text: 'INT', type: 'blue' };
			case 'decimal':
				return { text: 'DEC', type: 'cyan' };
			case 'date':
				return { text: 'DATE', type: 'purple' };
			case 'boolean':
				return { text: 'BOOL', type: 'teal' };
			case 'text':
			default:
				return { text: 'TEXT', type: 'green' };
		}
	}

	// Format cell value based on data type
	function formatCellValue(value: string | number | boolean | null | undefined, dataType: string): string {
		if (value === null || value === undefined) {
			return '';
		}

		switch (dataType) {
			case 'boolean':
				return value ? 'Yes' : 'No';
			case 'date':
				// Dates are stored as strings, display as-is
				return String(value);
			case 'decimal':
				// Format decimals with appropriate precision
				if (typeof value === 'number') {
					return value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 6 });
				}
				return String(value);
			case 'integer':
				if (typeof value === 'number') {
					return value.toLocaleString('en-US', { maximumFractionDigits: 0 });
				}
				return String(value);
			case 'text':
			default:
				return String(value);
		}
	}

	// Sort columns by position
	$: sortedColumns = table?.columns.slice().sort((a, b) => a.position - b.position) || [];

	// Back to tables list
	function handleBack() {
		goto('/tables');
	}

	// Handle column created
	function handleColumnCreated(event: CustomEvent<ColumnResponse>) {
		const newColumn = event.detail;
		if (table) {
			// Add new column to table
			table = {
				...table,
				columns: [...table.columns, newColumn]
			};
		}
		showAddColumnModal = false;
		toasts.success('Column added', `Column "${newColumn.name}" has been added to the table`);
	}

	// Handle single row add
	async function handleAddRow() {
		if (!table || sortedColumns.length === 0) {
			toasts.error('Cannot add row', 'Table must have at least one column defined');
			return;
		}

		addingRow = true;

		// Create a single empty row
		const emptyRow: { cells: CellData } = { cells: {} };
		const response = await api.post<RowResponse[]>(`/tables/${tableId}/rows`, { rows: [emptyRow] });

		if (response.error) {
			toasts.error('Failed to add row', response.error.message);
			addingRow = false;
			return;
		}

		if (response.data && response.data.length > 0) {
			const newRow = response.data[0];
			// Add new row to table
			table = {
				...table,
				rows: [...table.rows, newRow]
			};
			toasts.success('Row added', `Row ${newRow.row_index} has been added`);
		}

		addingRow = false;
	}

	// Handle multiple rows created from modal
	function handleMultipleRowsCreated(event: CustomEvent<RowResponse[]>) {
		const newRows = event.detail;
		if (table && newRows.length > 0) {
			table = {
				...table,
				rows: [...table.rows, ...newRows]
			};
		}
		showAddMultipleRowsModal = false;
		toasts.success(
			'Rows added',
			`${newRows.length} row${newRows.length !== 1 ? 's' : ''} added (indices ${newRows[0].row_index}${newRows.length > 1 ? `-${newRows[newRows.length - 1].row_index}` : ''})`
		);
	}

	// ================================================================
	// Inline Cell Editing
	// ================================================================

	// Start editing a cell
	async function startEditing(row: RowResponse, column: ColumnResponse) {
		if (!canEdit || savingCell) return;

		const currentValue = row.cells[column.name];
		editingCell = { rowId: row.id, columnName: column.name };
		originalValue = currentValue;
		editValue = currentValue;

		// For boolean, sync to the separate bool binding
		if (column.data_type === 'boolean') {
			editBoolValue = currentValue === true;
		}

		// Wait for DOM update then focus input
		await tick();
		if (cellInputRef) {
			cellInputRef.focus();
			// Select all text for text/number inputs
			if ('select' in cellInputRef && typeof cellInputRef.select === 'function') {
				cellInputRef.select();
			}
		}
	}

	// Cancel editing
	function cancelEditing() {
		editingCell = null;
		editValue = null;
		editBoolValue = false;
		originalValue = null;
	}

	// Save cell value
	async function saveCell() {
		if (!editingCell || !table || savingCell) return;

		const { rowId, columnName } = editingCell;
		const column = table.columns.find(c => c.name === columnName);
		if (!column) return;

		// For boolean, use the separate binding
		const rawValue = column.data_type === 'boolean' ? editBoolValue : editValue;

		// Validate and convert value based on data type
		let valueToSave = rawValue;

		try {
			valueToSave = validateAndConvertValue(rawValue, column.data_type);
		} catch (err) {
			toasts.error('Validation error', (err as Error).message);
			return;
		}

		// Check if value actually changed
		if (valueToSave === originalValue) {
			cancelEditing();
			return;
		}

		// Optimistic update - update UI immediately
		const rowIndex = table.rows.findIndex(r => r.id === rowId);
		if (rowIndex === -1) {
			cancelEditing();
			return;
		}

		const previousValue = table.rows[rowIndex].cells[columnName];
		table.rows[rowIndex].cells[columnName] = valueToSave;
		table = table; // Trigger reactivity

		savingCell = true;
		const savedEditingCell = { ...editingCell };

		// Send PATCH request
		const response = await api.patch<RowResponse>(`/tables/${tableId}/rows/${rowId}`, {
			[columnName]: valueToSave
		});

		savingCell = false;

		if (response.error) {
			// Rollback on error
			table.rows[rowIndex].cells[columnName] = previousValue;
			table = table;
			toasts.error('Failed to save', response.error.message);
		} else {
			// Update with server response
			if (response.data) {
				table.rows[rowIndex] = response.data;
				table = table;
			}
		}

		// Clear editing state
		if (editingCell?.rowId === savedEditingCell.rowId && editingCell?.columnName === savedEditingCell.columnName) {
			cancelEditing();
		}
	}

	// Validate and convert value based on data type
	function validateAndConvertValue(value: string | number | boolean | null, dataType: string): string | number | boolean | null {
		if (value === null || value === undefined || value === '') {
			return null;
		}

		switch (dataType) {
			case 'integer': {
				const num = parseInt(String(value), 10);
				if (isNaN(num)) {
					throw new Error('Value must be a valid integer');
				}
				return num;
			}
			case 'decimal': {
				const num = parseFloat(String(value));
				if (isNaN(num)) {
					throw new Error('Value must be a valid number');
				}
				return num;
			}
			case 'boolean': {
				if (typeof value === 'boolean') return value;
				const str = String(value).toLowerCase();
				if (str === 'true' || str === '1' || str === 'yes') return true;
				if (str === 'false' || str === '0' || str === 'no') return false;
				throw new Error('Value must be true/false');
			}
			case 'date': {
				const str = String(value);
				// Validate date format (YYYY-MM-DD)
				if (!/^\d{4}-\d{2}-\d{2}$/.test(str)) {
					throw new Error('Date must be in YYYY-MM-DD format');
				}
				const date = new Date(str);
				if (isNaN(date.getTime())) {
					throw new Error('Invalid date');
				}
				return str;
			}
			case 'text':
			default:
				return String(value);
		}
	}

	// Handle keyboard events in edit mode
	function handleKeyDown(event: KeyboardEvent, row: RowResponse, column: ColumnResponse) {
		if (!editingCell) return;

		switch (event.key) {
			case 'Escape':
				event.preventDefault();
				cancelEditing();
				break;
			case 'Enter':
				if (column.data_type !== 'text') {
					// For non-text types, Enter commits and moves down
					event.preventDefault();
					saveAndMoveDown(row, column);
				} else if (!event.shiftKey) {
					// For text, regular Enter commits and moves down
					event.preventDefault();
					saveAndMoveDown(row, column);
				}
				// Shift+Enter in text creates newline (default behavior)
				break;
			case 'Tab':
				event.preventDefault();
				if (event.shiftKey) {
					saveAndMovePrevious(row, column);
				} else {
					saveAndMoveNext(row, column);
				}
				break;
		}
	}

	// Save and move to next cell (Tab)
	async function saveAndMoveNext(row: RowResponse, column: ColumnResponse) {
		await saveCell();
		if (!table) return;

		const colIndex = sortedColumns.findIndex(c => c.name === column.name);
		const rowIndex = table.rows.findIndex(r => r.id === row.id);

		// Move to next column in same row
		if (colIndex < sortedColumns.length - 1) {
			startEditing(table.rows[rowIndex], sortedColumns[colIndex + 1]);
		} else if (rowIndex < table.rows.length - 1) {
			// Move to first column of next row
			startEditing(table.rows[rowIndex + 1], sortedColumns[0]);
		}
	}

	// Save and move to previous cell (Shift+Tab)
	async function saveAndMovePrevious(row: RowResponse, column: ColumnResponse) {
		await saveCell();
		if (!table) return;

		const colIndex = sortedColumns.findIndex(c => c.name === column.name);
		const rowIndex = table.rows.findIndex(r => r.id === row.id);

		// Move to previous column in same row
		if (colIndex > 0) {
			startEditing(table.rows[rowIndex], sortedColumns[colIndex - 1]);
		} else if (rowIndex > 0) {
			// Move to last column of previous row
			startEditing(table.rows[rowIndex - 1], sortedColumns[sortedColumns.length - 1]);
		}
	}

	// Save and move down (Enter)
	async function saveAndMoveDown(row: RowResponse, column: ColumnResponse) {
		await saveCell();
		if (!table) return;

		const rowIndex = table.rows.findIndex(r => r.id === row.id);

		// Move to same column in next row
		if (rowIndex < table.rows.length - 1) {
			startEditing(table.rows[rowIndex + 1], column);
		}
	}

	// Check if a cell is currently being edited
	function isEditing(rowId: string, columnName: string): boolean {
		return editingCell?.rowId === rowId && editingCell?.columnName === columnName;
	}

	// Handle blur event - save on blur unless clicking another cell
	function handleBlur(_event: FocusEvent) {
		// Small delay to check if focus moved to another cell
		setTimeout(() => {
			if (editingCell && !savingCell) {
				saveCell();
			}
		}, 100);
	}

	onMount(() => {
		// Set initial breadcrumbs (will update when data loads)
		breadcrumbs.set([
			{ label: 'Tables', href: '/tables' },
			{ label: 'Loading...' }
		]);
		fetchTable();
	});
</script>

<svelte:head>
	<title>{table?.name || 'Table Detail'} - Assumptions Manager</title>
</svelte:head>

<Grid>
	<!-- Back button and header -->
	<Row>
		<Column>
			<Button
				kind="ghost"
				icon={ArrowLeft}
				on:click={handleBack}
				class="back-button"
			>
				Back to Tables
			</Button>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error loading table"
					subtitle={error}
					lowContrast
					on:close={() => (error = null)}
				/>
			</Column>
		</Row>
	{/if}

	{#if loading}
		<!-- Loading skeleton -->
		<Row>
			<Column>
				<div class="header-skeleton">
					<SkeletonText heading width="40%" />
					<SkeletonText width="60%" />
				</div>
			</Column>
		</Row>
		<Row>
			<Column lg={4} md={4} sm={4}>
				<SkeletonPlaceholder style="height: 80px; width: 100%;" />
			</Column>
			<Column lg={4} md={4} sm={4}>
				<SkeletonPlaceholder style="height: 80px; width: 100%;" />
			</Column>
			<Column lg={4} md={4} sm={4}>
				<SkeletonPlaceholder style="height: 80px; width: 100%;" />
			</Column>
		</Row>
		<Row>
			<Column>
				<div class="grid-skeleton">
					<SkeletonPlaceholder style="height: 400px; width: 100%;" />
				</div>
			</Column>
		</Row>
	{:else if table}
		<!-- Table header with metadata -->
		<Row>
			<Column>
				<div class="table-header">
					<div class="table-header-top">
						<h1 class="table-name">{table.name}</h1>
						<div class="header-actions">
							{#if canEdit}
								{#if selectedRowCount > 0}
									<Button
										kind="danger"
										icon={TrashCan}
										on:click={handleOpenDeleteRowsModal}
									>
										Delete Selected ({selectedRowCount})
									</Button>
									<Button
										kind="ghost"
										size="small"
										on:click={clearSelection}
									>
										Clear Selection
									</Button>
								{:else}
									<Button
										kind="tertiary"
										icon={RowInsert}
										on:click={handleAddRow}
										disabled={addingRow || sortedColumns.length === 0}
									>
										{addingRow ? 'Adding...' : 'Add Row'}
									</Button>
									<Button
										kind="ghost"
										size="small"
										on:click={() => (showAddMultipleRowsModal = true)}
										disabled={addingRow || sortedColumns.length === 0}
									>
										Add Multiple
									</Button>
									<Button
										kind="primary"
										icon={Add}
										on:click={() => (showAddColumnModal = true)}
									>
										Add Column
									</Button>
								{/if}
								{#if canDelete}
									<Button
										kind="danger-ghost"
										icon={TrashCan}
										on:click={() => (showDeleteTableModal = true)}
									>
										Delete Table
									</Button>
								{/if}
							{/if}
							<!-- Version History visible to all users -->
							<Button
								kind="ghost"
								icon={RecentlyViewed}
								on:click={() => goto(`/tables/${tableId}/versions`)}
							>
								Version History
							</Button>
						</div>
					</div>
					{#if table.description}
						<p class="table-description">{table.description}</p>
					{/if}
				</div>
			</Column>
		</Row>

		<!-- Metadata tiles -->
		<Row class="metadata-row">
			<Column lg={4} md={4} sm={4}>
				<Tile class="metadata-tile">
					<div class="metadata-label">
						<Calendar size={16} />
						<span>Created</span>
					</div>
					<div class="metadata-value">{formatDateTime(table.created_at)}</div>
				</Tile>
			</Column>
			<Column lg={4} md={4} sm={4}>
				<Tile class="metadata-tile">
					<div class="metadata-label">
						<Time size={16} />
						<span>Last Modified</span>
					</div>
					<div class="metadata-value">{formatDateTime(table.updated_at || table.created_at)}</div>
				</Tile>
			</Column>
			{#if table.effective_date}
				<Column lg={4} md={4} sm={4}>
					<Tile class="metadata-tile">
						<div class="metadata-label">
							<Calendar size={16} />
							<span>Effective Date</span>
						</div>
						<div class="metadata-value">{formatDate(table.effective_date)}</div>
					</Tile>
				</Column>
			{/if}
		</Row>

		<!-- Data grid -->
		<Row>
			<Column>
				<div class="data-grid-container">
					{#if sortedColumns.length === 0}
						<!-- No columns yet -->
						<div class="empty-state">
							<h3>No columns defined</h3>
							<p>This table doesn't have any columns yet. Add columns to start entering data.</p>
							{#if canEdit}
								<Button
									kind="primary"
									icon={Add}
									on:click={() => (showAddColumnModal = true)}
									class="empty-state-button"
								>
									Add Column
								</Button>
							{/if}
						</div>
					{:else if table.rows.length === 0}
						<!-- Columns but no rows -->
						<div class="data-grid-wrapper">
							<table class="data-grid">
								<thead>
									<tr>
										{#if canEdit}
											<th class="checkbox-header">
												<!-- No select-all for empty table -->
											</th>
										{/if}
										<th class="row-index-header">#</th>
										{#each sortedColumns as column}
											<th class="column-header">
												<div class="column-header-content">
													<span class="column-name">{column.name}</span>
													<Tag type={getDataTypeTag(column.data_type).type} size="sm">
														{getDataTypeTag(column.data_type).text}
													</Tag>
												</div>
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									<tr>
										<td colspan={sortedColumns.length + (canEdit ? 2 : 1)} class="empty-rows">
											<div class="empty-rows-content">
												<p>No data rows. Add rows to enter data.</p>
												{#if canEdit}
													<Button
														kind="primary"
														icon={RowInsert}
														size="small"
														on:click={handleAddRow}
														disabled={addingRow}
													>
														Add Row
													</Button>
												{/if}
											</div>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
					{:else}
						<!-- Full data grid -->
						<div class="data-grid-wrapper">
							<table class="data-grid">
								<thead>
									<tr>
										{#if canEdit}
											<th class="checkbox-header">
												<Checkbox
													checked={allRowsSelected}
													indeterminate={someRowsSelected}
													on:change={toggleAllRows}
													labelText="Select all rows"
													hideLabel
												/>
											</th>
										{/if}
										<th class="row-index-header">#</th>
										{#each sortedColumns as column}
											<th class="column-header">
												<div class="column-header-content">
													<span class="column-name">{column.name}</span>
													<Tag type={getDataTypeTag(column.data_type).type} size="sm">
														{getDataTypeTag(column.data_type).text}
													</Tag>
												</div>
											</th>
										{/each}
									</tr>
								</thead>
								<tbody>
									{#each table.rows as row}
										<tr class:selected-row={selectedRowIds.has(row.id)}>
											{#if canEdit}
												<td class="checkbox-cell">
													<Checkbox
														checked={selectedRowIds.has(row.id)}
														on:change={() => toggleRowSelection(row.id)}
														labelText="Select row {row.row_index}"
														hideLabel
													/>
												</td>
											{/if}
											<td class="row-index-cell">{row.row_index}</td>
											{#each sortedColumns as column}
												{@const cellValue = row.cells[column.name]}
												{@const formattedValue = formatCellValue(cellValue, column.data_type)}
												{@const editing = isEditing(row.id, column.name)}
												<td
													class="data-cell"
													class:empty-cell={!editing && (cellValue === null || cellValue === undefined || cellValue === '')}
													class:boolean-cell={column.data_type === 'boolean'}
													class:number-cell={column.data_type === 'integer' || column.data_type === 'decimal'}
													class:editable={canEdit}
													class:editing={editing}
													on:click={() => !editing && canEdit && startEditing(row, column)}
													on:keydown={(e) => e.key === 'Enter' && !editing && canEdit && startEditing(row, column)}
													tabindex={canEdit && !editing ? 0 : -1}
													role={canEdit ? 'gridcell' : undefined}
												>
													{#if editing}
														<!-- Edit mode: show appropriate input based on data type -->
														<div class="cell-editor" role="presentation" on:keydown={(e) => handleKeyDown(e, row, column)}>
															{#if column.data_type === 'boolean'}
																<Checkbox
																	bind:checked={editBoolValue}
																	on:blur={handleBlur}
																	labelText=""
																	hideLabel
																/>
															{:else if column.data_type === 'integer'}
																<input
																	type="number"
																	class="cell-input number-input"
																	bind:value={editValue}
																	bind:this={cellInputRef}
																	on:blur={handleBlur}
																	step="1"
																/>
															{:else if column.data_type === 'decimal'}
																<input
																	type="number"
																	class="cell-input number-input"
																	bind:value={editValue}
																	bind:this={cellInputRef}
																	on:blur={handleBlur}
																	step="any"
																/>
															{:else if column.data_type === 'date'}
																<input
																	type="date"
																	class="cell-input date-input"
																	bind:value={editValue}
																	bind:this={cellInputRef}
																	on:blur={handleBlur}
																/>
															{:else}
																<input
																	type="text"
																	class="cell-input text-input"
																	bind:value={editValue}
																	bind:this={cellInputRef}
																	on:blur={handleBlur}
																/>
															{/if}
														</div>
													{:else if cellValue === null || cellValue === undefined || cellValue === ''}
														<span class="empty-placeholder">—</span>
													{:else}
														{formattedValue}
													{/if}
												</td>
											{/each}
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{/if}
				</div>
			</Column>
		</Row>

		<!-- Summary info -->
		<Row>
			<Column>
				<div class="summary-info">
					<span>{sortedColumns.length} column{sortedColumns.length !== 1 ? 's' : ''}</span>
					<span class="separator">•</span>
					<span>{table.rows.length} row{table.rows.length !== 1 ? 's' : ''}</span>
				</div>
			</Column>
		</Row>
	{/if}
</Grid>

<!-- Add Column Modal -->
<AddColumnModal
	bind:open={showAddColumnModal}
	tableId={tableId}
	existingColumnNames={existingColumnNames}
	on:close={() => (showAddColumnModal = false)}
	on:created={handleColumnCreated}
/>

<!-- Add Multiple Rows Modal -->
<AddMultipleRowsModal
	bind:open={showAddMultipleRowsModal}
	tableId={tableId}
	on:close={() => (showAddMultipleRowsModal = false)}
	on:created={handleMultipleRowsCreated}
/>

<!-- Delete Rows Modal -->
<DeleteRowsModal
	bind:open={showDeleteRowsModal}
	tableId={tableId}
	rows={selectedRows}
	on:close={() => (showDeleteRowsModal = false)}
	on:deleted={handleRowsDeleted}
/>

<!-- Delete Table Modal -->
{#if table}
	<DeleteTableModal
		bind:open={showDeleteTableModal}
		tableId={tableId}
		tableName={table.name}
		rowCount={table.rows.length}
		on:close={() => (showDeleteTableModal = false)}
		on:deleted={handleTableDeleted}
	/>
{/if}

<style>
	:global(.back-button) {
		margin-bottom: 1rem;
	}

	.header-skeleton {
		margin-bottom: 1.5rem;
	}

	.grid-skeleton {
		margin-top: 1.5rem;
	}

	.table-header {
		margin-bottom: 1.5rem;
	}

	.table-header-top {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: 1rem;
	}

	.header-actions {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		flex-shrink: 0;
	}

	.table-name {
		font-size: 2rem;
		font-weight: 400;
		margin-bottom: 0.5rem;
	}

	.table-description {
		color: var(--cds-text-secondary, #525252);
		font-size: 1rem;
	}

	:global(.metadata-row) {
		margin-bottom: 1.5rem;
	}

	:global(.metadata-tile) {
		height: 100%;
	}

	.metadata-label {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		color: var(--cds-text-secondary, #525252);
		font-size: 0.875rem;
		margin-bottom: 0.25rem;
	}

	.metadata-value {
		font-size: 1rem;
		font-weight: 500;
	}

	.data-grid-container {
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
		padding: 1rem;
	}

	.data-grid-wrapper {
		overflow-x: auto;
		overflow-y: auto;
		max-height: 600px;
		border: 1px solid var(--cds-border-subtle-01, #e0e0e0);
		border-radius: 4px;
		background: var(--cds-layer-02, #ffffff);
	}

	.data-grid {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
	}

	.data-grid thead {
		position: sticky;
		top: 0;
		z-index: 1;
	}

	.row-index-header,
	.column-header {
		background: var(--cds-layer-accent-01, #e0e0e0);
		padding: 0.75rem 1rem;
		text-align: left;
		font-weight: 600;
		border-bottom: 2px solid var(--cds-border-strong-01, #8d8d8d);
		white-space: nowrap;
	}

	.row-index-header {
		width: 60px;
		min-width: 60px;
		text-align: center;
		color: var(--cds-text-secondary, #525252);
	}

	.column-header-content {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.column-name {
		font-weight: 600;
	}

	.row-index-cell,
	.data-cell {
		padding: 0.5rem 1rem;
		border-bottom: 1px solid var(--cds-border-subtle-01, #e0e0e0);
		vertical-align: middle;
	}

	.row-index-cell {
		background: var(--cds-layer-01, #f4f4f4);
		text-align: center;
		color: var(--cds-text-secondary, #525252);
		font-weight: 500;
		width: 60px;
		min-width: 60px;
	}

	.data-cell {
		min-width: 120px;
		max-width: 300px;
	}

	.number-cell {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.boolean-cell {
		text-align: center;
	}

	.empty-cell {
		background: var(--cds-layer-01, #f4f4f4);
	}

	.empty-placeholder {
		color: var(--cds-text-disabled, #c6c6c6);
	}

	.data-grid tbody tr:hover {
		background: var(--cds-layer-hover-01, #e8e8e8);
	}

	.data-grid tbody tr:nth-child(even) {
		background: var(--cds-layer-01, #f4f4f4);
	}

	.data-grid tbody tr:nth-child(even):hover {
		background: var(--cds-layer-hover-01, #e8e8e8);
	}

	.empty-rows {
		text-align: center;
		padding: 2rem 1rem;
		color: var(--cds-text-secondary, #525252);
	}

	.empty-rows-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1rem;
	}

	.empty-rows-content p {
		margin: 0;
	}

	.empty-state {
		text-align: center;
		padding: 3rem 1rem;
	}

	.empty-state h3 {
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

	.empty-state p {
		color: var(--cds-text-secondary, #525252);
		margin-bottom: 1rem;
	}

	:global(.empty-state-button) {
		margin-top: 0.5rem;
	}

	.summary-info {
		margin-top: 1rem;
		color: var(--cds-text-secondary, #525252);
		font-size: 0.875rem;
	}

	.separator {
		margin: 0 0.5rem;
	}

	/* Editable cell styles */
	.data-cell.editable {
		cursor: pointer;
		transition: background-color 0.1s ease;
	}

	.data-cell.editable:hover {
		background: var(--cds-layer-selected-01, #e0e0e0);
	}

	.data-cell.editable:focus {
		outline: 2px solid var(--cds-focus, #0f62fe);
		outline-offset: -2px;
	}

	.data-cell.editing {
		padding: 0;
		background: var(--cds-layer-02, #ffffff);
	}

	.cell-editor {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
	}

	.cell-input {
		width: 100%;
		padding: 0.5rem 1rem;
		border: 2px solid var(--cds-focus, #0f62fe);
		background: var(--cds-field-01, #ffffff);
		font-size: 0.875rem;
		font-family: inherit;
		outline: none;
	}

	.cell-input:focus {
		border-color: var(--cds-focus, #0f62fe);
	}

	.cell-input.number-input {
		text-align: right;
		font-variant-numeric: tabular-nums;
	}

	.cell-input.date-input {
		min-width: 150px;
	}

	/* Carbon Checkbox in cell */
	.cell-editor :global(.bx--checkbox-wrapper) {
		justify-content: center;
		padding: 0.5rem 1rem;
	}

	.cell-editor :global(.bx--checkbox-label) {
		padding-left: 0;
	}

	/* Remove spinner buttons from number inputs */
	.cell-input.number-input::-webkit-outer-spin-button,
	.cell-input.number-input::-webkit-inner-spin-button {
		-webkit-appearance: none;
		margin: 0;
	}

	.cell-input.number-input {
		appearance: textfield;
		-moz-appearance: textfield;
	}

	/* Checkbox column styles */
	.checkbox-header,
	.checkbox-cell {
		width: 48px;
		min-width: 48px;
		max-width: 48px;
		padding: 0.5rem;
		text-align: center;
		background: var(--cds-layer-accent-01, #e0e0e0);
	}

	.checkbox-cell {
		background: inherit;
	}

	/* Selected row highlight */
	.data-grid tbody tr.selected-row {
		background: var(--cds-layer-selected-01, #e0e0e0);
	}

	.data-grid tbody tr.selected-row:hover {
		background: var(--cds-layer-selected-hover-01, #d1d1d1);
	}

	/* Checkbox alignment in cells */
	.checkbox-header :global(.bx--checkbox-wrapper),
	.checkbox-cell :global(.bx--checkbox-wrapper) {
		justify-content: center;
	}

	.checkbox-header :global(.bx--checkbox-label),
	.checkbox-cell :global(.bx--checkbox-label) {
		padding-left: 0;
	}
</style>
