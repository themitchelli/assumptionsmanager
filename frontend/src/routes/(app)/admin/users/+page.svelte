<script lang="ts">
	import { onMount } from 'svelte';
	import {
		Grid,
		Row,
		Column,
		DataTable,
		Toolbar,
		ToolbarContent,
		ToolbarSearch,
		Dropdown,
		Pagination,
		Tag,
		Button,
		SkeletonText,
		ToastNotification
	} from 'carbon-components-svelte';
	import { Add, Edit, TrashCan } from 'carbon-icons-svelte';
	import { breadcrumbs } from '$lib/stores/navigation';
	import { auth } from '$lib/stores/auth';
	import { api } from '$lib/api';
	import { toasts } from '$lib/stores/toast';
	import type { UserResponse } from '$lib/api/types';
	import AddUserModal from '$lib/components/AddUserModal.svelte';

	// State
	let users: UserResponse[] = [];
	let loading = true;
	let error: string | null = null;

	// Modal state
	let addUserModalOpen = false;

	// Filtering
	let searchQuery = '';
	let selectedRole = 'all';
	const roleOptions = [
		{ id: 'all', text: 'All Roles' },
		{ id: 'viewer', text: 'Viewer' },
		{ id: 'analyst', text: 'Analyst' },
		{ id: 'admin', text: 'Admin' },
		{ id: 'super_admin', text: 'Super Admin' }
	];

	// Pagination
	let page = 1;
	let pageSize = 10;
	const pageSizes = [10, 25, 50];

	// Sorting
	let sortKey: string = 'email';
	let sortDirection: 'ascending' | 'descending' | 'none' = 'ascending';

	// Computed filtered and sorted data
	$: filteredUsers = users.filter((user) => {
		const matchesSearch =
			searchQuery === '' ||
			user.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
			(user.name && user.name.toLowerCase().includes(searchQuery.toLowerCase()));
		const matchesRole = selectedRole === 'all' || user.role === selectedRole;
		return matchesSearch && matchesRole;
	});

	$: sortedUsers = [...filteredUsers].sort((a, b) => {
		if (sortDirection === 'none') return 0;
		const modifier = sortDirection === 'ascending' ? 1 : -1;
		const aVal = getSortValue(a, sortKey);
		const bVal = getSortValue(b, sortKey);
		if (aVal < bVal) return -1 * modifier;
		if (aVal > bVal) return 1 * modifier;
		return 0;
	});

	$: paginatedUsers = sortedUsers.slice((page - 1) * pageSize, page * pageSize);

	$: totalItems = filteredUsers.length;

	function getSortValue(user: UserResponse, key: string): string | number {
		switch (key) {
			case 'email':
				return user.email.toLowerCase();
			case 'name':
				return (user.name || user.email).toLowerCase();
			case 'role':
				return user.role;
			case 'created_at':
				return new Date(user.created_at).getTime();
			default:
				return '';
		}
	}

	// DataTable headers - sort: false disables sorting for that column
	const headers = [
		{ key: 'name', value: 'Name' },
		{ key: 'email', value: 'Email' },
		{ key: 'role', value: 'Role' },
		{ key: 'created_at', value: 'Created' },
		{ key: 'actions', value: 'Actions', sort: false as const }
	];

	// Formatted rows for DataTable
	$: rows = paginatedUsers.map((user) => ({
		id: user.id,
		name: user.name || user.email.split('@')[0],
		email: user.email,
		role: user.role,
		roleDisplay: getRoleDisplay(user.role),
		created_at: formatDate(user.created_at),
		isCurrentUser: user.id === $auth.user?.id
	}));

	function getRoleDisplay(role: string): { text: string; type: 'blue' | 'green' | 'purple' | 'red' } {
		switch (role) {
			case 'super_admin':
				return { text: 'Super Admin', type: 'red' };
			case 'admin':
				return { text: 'Admin', type: 'purple' };
			case 'analyst':
				return { text: 'Analyst', type: 'green' };
			case 'viewer':
			default:
				return { text: 'Viewer', type: 'blue' };
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('en-GB', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	function handleSort(event: CustomEvent<{ header: { key: string }; sortDirection?: 'ascending' | 'descending' | 'none' }>) {
		sortKey = event.detail.header.key;
		sortDirection = event.detail.sortDirection || 'none';
	}

	function handleEdit(userId: string) {
		// TODO: Implement in US-003
		console.log('Edit user:', userId);
	}

	function handleDelete(userId: string) {
		// TODO: Implement in US-004
		console.log('Delete user:', userId);
	}

	function handleAddUser() {
		addUserModalOpen = true;
	}

	function handleUserCreated(event: CustomEvent<UserResponse>) {
		const newUser = event.detail;
		users = [...users, newUser];
		addUserModalOpen = false;
		toasts.add({
			kind: 'success',
			title: 'User added',
			subtitle: `${newUser.email} has been added to your organization`
		});
	}

	// Get existing emails for duplicate validation in modal
	$: existingEmails = users.map((u) => u.email);

	async function fetchUsers() {
		loading = true;
		error = null;
		const response = await api.get<UserResponse[]>('/users');
		if (response.error) {
			error = response.error.message;
		} else if (response.data) {
			users = response.data;
		}
		loading = false;
	}

	onMount(() => {
		breadcrumbs.set([{ label: 'Admin', href: '/admin/users' }, { label: 'Users' }]);
		fetchUsers();
	});
</script>

<svelte:head>
	<title>Users - Admin - Assumptions Manager</title>
</svelte:head>

<Grid>
	<Row>
		<Column>
			<h1 class="page-title">User Management</h1>
			<p class="page-description">Manage users within your organization</p>
		</Column>
	</Row>

	{#if error}
		<Row>
			<Column>
				<ToastNotification
					kind="error"
					title="Error"
					subtitle={error}
					lowContrast
					on:close={() => (error = null)}
				/>
			</Column>
		</Row>
	{/if}

	<Row>
		<Column>
			{#if loading}
				<div class="skeleton-container">
					<SkeletonText heading />
					<SkeletonText paragraph lines={5} />
				</div>
			{:else if users.length === 0}
				<div class="empty-state">
					<h3>No users found</h3>
					<p>There are no other users in your organization yet.</p>
					<Button icon={Add} on:click={handleAddUser}>Add User</Button>
				</div>
			{:else}
				<DataTable
					{headers}
					{rows}
					sortable
					on:click:header={handleSort}
					size="medium"
				>
					<Toolbar>
						<ToolbarContent>
							<ToolbarSearch
								bind:value={searchQuery}
								placeholder="Search by name or email..."
								persistent
							/>
							<Dropdown
								titleText=""
								hideLabel
								bind:selectedId={selectedRole}
								items={roleOptions}
								style="min-width: 150px;"
							/>
							<Button icon={Add} on:click={handleAddUser}>Add User</Button>
						</ToolbarContent>
					</Toolbar>
					<svelte:fragment slot="cell" let:row let:cell>
						{#if cell.key === 'role'}
							<Tag type={row.roleDisplay.type}>{row.roleDisplay.text}</Tag>
						{:else if cell.key === 'actions'}
							<div class="action-buttons">
								<Button
									kind="ghost"
									size="small"
									icon={Edit}
									iconDescription="Edit user"
									on:click={() => handleEdit(row.id)}
									disabled={row.isCurrentUser}
								/>
								<Button
									kind="ghost"
									size="small"
									icon={TrashCan}
									iconDescription="Delete user"
									on:click={() => handleDelete(row.id)}
									disabled={row.isCurrentUser || (row.role === 'admin' && $auth.user?.role !== 'super_admin')}
								/>
							</div>
						{:else}
							{cell.value}
						{/if}
					</svelte:fragment>
				</DataTable>

				<Pagination
					bind:pageSize
					bind:page
					{totalItems}
					{pageSizes}
					on:update={(e) => {
						page = e.detail.page;
						pageSize = e.detail.pageSize;
					}}
				/>
			{/if}
		</Column>
	</Row>
</Grid>

<AddUserModal
	bind:open={addUserModalOpen}
	{existingEmails}
	on:close={() => (addUserModalOpen = false)}
	on:created={handleUserCreated}
/>

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

	.skeleton-container {
		padding: 1rem;
	}

	.empty-state {
		text-align: center;
		padding: 3rem 1rem;
		background: var(--cds-layer-01, #f4f4f4);
		border-radius: 4px;
	}

	.empty-state h3 {
		margin-bottom: 0.5rem;
		font-weight: 600;
	}

	.empty-state p {
		margin-bottom: 1.5rem;
		color: var(--cds-text-secondary, #525252);
	}

	.action-buttons {
		display: flex;
		gap: 0.25rem;
	}

	:global(.bx--data-table) {
		margin-bottom: 1rem;
	}

	:global(.bx--toolbar-content) {
		gap: 0.5rem;
	}
</style>
