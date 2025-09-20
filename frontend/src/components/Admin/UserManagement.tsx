import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Switch,
  FormControlLabel,
  Alert,
  Tooltip,
  Grid,
  Card,
  CardContent
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Visibility as ViewIcon,
  Person as PersonIcon,
  AdminPanelSettings as AdminIcon,
  Engineering as EngineerIcon,
  Build as OperatorIcon,
  RemoveRedEye as ViewerIcon
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';

import { adminService, User, UserCreate, UserUpdate } from '../../services/adminService';

interface UserFormData {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role: 'engineer' | 'admin' | 'operator' | 'viewer';
  professional_license: string;
  license_expiry: Date | null;
  organization: string;
  employee_id: string;
  is_active: boolean;
  is_verified: boolean;
}

const initialFormData: UserFormData = {
  username: '',
  email: '',
  full_name: '',
  password: '',
  role: 'viewer',
  professional_license: '',
  license_expiry: null,
  organization: '',
  employee_id: '',
  is_active: true,
  is_verified: false
};

export const UserManagement: React.FC = () => {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState<UserFormData>(initialFormData);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const usersData = await adminService.getUsers();
      setUsers(usersData);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load users:', err);
      setError(err.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = () => {
    setEditingUser(null);
    setFormData(initialFormData);
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    setFormData({
      username: user.username,
      email: user.email,
      full_name: user.full_name,
      password: '', // Don't populate password for editing
      role: user.role,
      professional_license: user.professional_license || '',
      license_expiry: user.license_expiry ? new Date(user.license_expiry) : null,
      organization: user.organization || '',
      employee_id: user.employee_id || '',
      is_active: user.is_active,
      is_verified: user.is_verified
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.username.trim()) {
      errors.username = 'Username is required';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      errors.username = 'Username can only contain letters, numbers, underscores, and dashes';
    }

    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Invalid email format';
    }

    if (!formData.full_name.trim()) {
      errors.full_name = 'Full name is required';
    }

    if (!editingUser && !formData.password) {
      errors.password = 'Password is required for new users';
    } else if (formData.password && formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters long';
    }

    if (formData.role === 'engineer' && !formData.professional_license.trim()) {
      errors.professional_license = 'Professional license is required for engineers';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setSubmitting(true);
    try {
      if (editingUser) {
        // Update existing user
        const updateData: UserUpdate = {
          email: formData.email,
          full_name: formData.full_name,
          role: formData.role,
          is_active: formData.is_active,
          is_verified: formData.is_verified,
          professional_license: formData.professional_license || undefined,
          license_expiry: formData.license_expiry?.toISOString() || undefined,
          organization: formData.organization || undefined,
          employee_id: formData.employee_id || undefined
        };
        
        await adminService.updateUser(editingUser.id, updateData);
      } else {
        // Create new user
        const createData: UserCreate = {
          username: formData.username,
          email: formData.email,
          full_name: formData.full_name,
          password: formData.password,
          role: formData.role,
          professional_license: formData.professional_license || undefined,
          license_expiry: formData.license_expiry?.toISOString() || undefined,
          organization: formData.organization || undefined,
          employee_id: formData.employee_id || undefined
        };
        
        await adminService.createUser(createData);
      }

      setDialogOpen(false);
      await loadUsers();
    } catch (err: any) {
      console.error('Failed to save user:', err);
      setError(err.message || 'Failed to save user');
    } finally {
      setSubmitting(false);
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin':
        return <AdminIcon />;
      case 'engineer':
        return <EngineerIcon />;
      case 'operator':
        return <OperatorIcon />;
      case 'viewer':
        return <ViewerIcon />;
      default:
        return <PersonIcon />;
    }
  };

  const getRoleColor = (role: string): 'primary' | 'secondary' | 'success' | 'warning' => {
    switch (role) {
      case 'admin':
        return 'primary';
      case 'engineer':
        return 'success';
      case 'operator':
        return 'warning';
      case 'viewer':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading users...</Typography>
      </Box>
    );
  }

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        {/* Header */}
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
          <Typography variant="h5" component="h2">
            User Management
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateUser}
          >
            Create User
          </Button>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* User Statistics */}
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Total Users</Typography>
                <Typography variant="h4">{users.length}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Active Users</Typography>
                <Typography variant="h4">
                  {users.filter(u => u.is_active).length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Engineers</Typography>
                <Typography variant="h4">
                  {users.filter(u => u.role === 'engineer').length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Can Sign-off</Typography>
                <Typography variant="h4">
                  {users.filter(u => u.can_sign_off).length}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Users Table */}
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>User</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Professional License</TableCell>
                <TableCell>Organization</TableCell>
                <TableCell>Last Login</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {user.full_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {user.username} • {user.email}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={getRoleIcon(user.role)}
                      label={user.role}
                      color={getRoleColor(user.role)}
                      size="small"
                      sx={{ textTransform: 'capitalize' }}
                    />
                  </TableCell>
                  <TableCell>
                    <Box display="flex" flexDirection="column" gap={0.5}>
                      <Chip
                        label={user.is_active ? 'Active' : 'Inactive'}
                        color={user.is_active ? 'success' : 'default'}
                        size="small"
                      />
                      {user.is_verified && (
                        <Chip
                          label="Verified"
                          color="primary"
                          size="small"
                        />
                      )}
                      {user.can_sign_off && (
                        <Chip
                          label="Can Sign-off"
                          color="success"
                          size="small"
                        />
                      )}
                      {user.is_locked && (
                        <Chip
                          label="Locked"
                          color="error"
                          size="small"
                        />
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {user.professional_license ? (
                      <Box>
                        <Typography variant="body2">
                          {user.professional_license}
                        </Typography>
                        {user.license_expiry && (
                          <Typography variant="body2" color="text.secondary">
                            Expires: {new Date(user.license_expiry).toLocaleDateString()}
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      <Typography variant="body2" color="text.secondary">
                        None
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {user.organization || 'Not specified'}
                    </Typography>
                    {user.employee_id && (
                      <Typography variant="body2" color="text.secondary">
                        ID: {user.employee_id}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {user.last_login_at 
                        ? new Date(user.last_login_at).toLocaleDateString()
                        : 'Never'
                      }
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Tooltip title="Edit User">
                      <IconButton
                        size="small"
                        onClick={() => handleEditUser(user)}
                      >
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>

        {/* User Form Dialog */}
        <Dialog 
          open={dialogOpen} 
          onClose={() => setDialogOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogTitle>
            {editingUser ? 'Edit User' : 'Create New User'}
          </DialogTitle>
          <DialogContent>
            <Grid container spacing={2} sx={{ mt: 1 }}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Username"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  error={!!formErrors.username}
                  helperText={formErrors.username}
                  disabled={!!editingUser} // Can't change username when editing
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  error={!!formErrors.email}
                  helperText={formErrors.email}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Full Name"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  error={!!formErrors.full_name}
                  helperText={formErrors.full_name}
                />
              </Grid>
              {!editingUser && (
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Password"
                    type="password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    error={!!formErrors.password}
                    helperText={formErrors.password}
                  />
                </Grid>
              )}
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Role</InputLabel>
                  <Select
                    value={formData.role}
                    label="Role"
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as any })}
                  >
                    <MenuItem value="viewer">Viewer</MenuItem>
                    <MenuItem value="operator">Operator</MenuItem>
                    <MenuItem value="engineer">Engineer</MenuItem>
                    <MenuItem value="admin">Admin</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Professional License"
                  value={formData.professional_license}
                  onChange={(e) => setFormData({ ...formData, professional_license: e.target.value })}
                  error={!!formErrors.professional_license}
                  helperText={formErrors.professional_license || (formData.role === 'engineer' ? 'Required for engineers' : '')}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <DatePicker
                  label="License Expiry"
                  value={formData.license_expiry}
                  onChange={(date) => setFormData({ ...formData, license_expiry: date })}
                  slotProps={{
                    textField: {
                      fullWidth: true
                    }
                  }}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Organization"
                  value={formData.organization}
                  onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Employee ID"
                  value={formData.employee_id}
                  onChange={(e) => setFormData({ ...formData, employee_id: e.target.value })}
                />
              </Grid>
              {editingUser && (
                <>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={formData.is_active}
                          onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                        />
                      }
                      label="Active"
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={formData.is_verified}
                          onChange={(e) => setFormData({ ...formData, is_verified: e.target.checked })}
                        />
                      }
                      label="Verified"
                    />
                  </Grid>
                </>
              )}
            </Grid>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleSubmit}
              variant="contained"
              disabled={submitting}
            >
              {submitting ? 'Saving...' : (editingUser ? 'Update' : 'Create')}
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
};