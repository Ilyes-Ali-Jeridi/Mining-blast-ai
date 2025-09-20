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
  Alert,
  Tooltip,
  Grid,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Visibility as ViewIcon,
  CheckCircle as ValidateIcon,
  Download as ExportIcon,
  Upload as ImportIcon,
  ExpandMore as ExpandMoreIcon,
  Settings as ConfigIcon,
  History as HistoryIcon
} from '@mui/icons-material';

import { adminService, Configuration } from '../../services/adminService';

export const ConfigurationManager: React.FC = () => {
  const [configurations, setConfigurations] = useState<Configuration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [validateDialogOpen, setValidateDialogOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<Configuration | null>(null);
  const [validationNotes, setValidationNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [filters, setFilters] = useState({
    config_type: '',
    scope: '',
    active_only: true
  });

  useEffect(() => {
    loadConfigurations();
  }, [filters]);

  const loadConfigurations = async () => {
    try {
      setLoading(true);
      const configs = await adminService.getConfigurations(filters);
      setConfigurations(configs);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load configurations:', err);
      setError(err.message || 'Failed to load configurations');
    } finally {
      setLoading(false);
    }
  };

  const handleViewConfig = (config: Configuration) => {
    setSelectedConfig(config);
    setViewDialogOpen(true);
  };

  const handleValidateConfig = (config: Configuration) => {
    setSelectedConfig(config);
    setValidationNotes('');
    setValidateDialogOpen(true);
  };

  const handleValidateSubmit = async () => {
    if (!selectedConfig) return;

    setSubmitting(true);
    try {
      await adminService.validateConfiguration(selectedConfig.id, validationNotes);
      setSuccess(`Configuration "${selectedConfig.config_name}" validated successfully`);
      setValidateDialogOpen(false);
      await loadConfigurations();
    } catch (err: any) {
      console.error('Failed to validate configuration:', err);
      setError(err.message || 'Failed to validate configuration');
    } finally {
      setSubmitting(false);
    }
  };

  const handleExportConfig = async (config: Configuration) => {
    try {
      const blob = await adminService.exportConfiguration(config.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `config_${config.config_key}_v${config.version}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error('Failed to export configuration:', err);
      setError(err.message || 'Failed to export configuration');
    }
  };

  const getTypeColor = (type: string): 'primary' | 'secondary' | 'success' | 'warning' | 'error' => {
    switch (type) {
      case 'physics':
        return 'primary';
      case 'safety':
        return 'error';
      case 'explosives':
        return 'warning';
      case 'optimization':
        return 'success';
      default:
        return 'secondary';
    }
  };

  const getScopeColor = (scope: string): 'primary' | 'secondary' | 'success' => {
    switch (scope) {
      case 'global':
        return 'primary';
      case 'site':
        return 'success';
      case 'user':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading configurations...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Configuration Management
        </Typography>
        <Button
          variant="outlined"
          startIcon={<ImportIcon />}
          onClick={() => {/* TODO: Implement import */}}
        >
          Import Config
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Filters</Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Configuration Type</InputLabel>
                <Select
                  value={filters.config_type}
                  label="Configuration Type"
                  onChange={(e) => setFilters({ ...filters, config_type: e.target.value })}
                >
                  <MenuItem value="">All Types</MenuItem>
                  <MenuItem value="physics">Physics</MenuItem>
                  <MenuItem value="safety">Safety</MenuItem>
                  <MenuItem value="explosives">Explosives</MenuItem>
                  <MenuItem value="optimization">Optimization</MenuItem>
                  <MenuItem value="equipment">Equipment</MenuItem>
                  <MenuItem value="system">System</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Scope</InputLabel>
                <Select
                  value={filters.scope}
                  label="Scope"
                  onChange={(e) => setFilters({ ...filters, scope: e.target.value })}
                >
                  <MenuItem value="">All Scopes</MenuItem>
                  <MenuItem value="global">Global</MenuItem>
                  <MenuItem value="site">Site</MenuItem>
                  <MenuItem value="user">User</MenuItem>
                  <MenuItem value="session">Session</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={4}>
              <FormControl fullWidth size="small">
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.active_only ? 'active' : 'all'}
                  label="Status"
                  onChange={(e) => setFilters({ ...filters, active_only: e.target.value === 'active' })}
                >
                  <MenuItem value="all">All Configurations</MenuItem>
                  <MenuItem value="active">Active Only</MenuItem>
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Configuration Statistics */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Total Configurations</Typography>
              <Typography variant="h4">{configurations.length}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Validated</Typography>
              <Typography variant="h4">
                {configurations.filter(c => c.is_validated).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Default Configs</Typography>
              <Typography variant="h4">
                {configurations.filter(c => c.is_default).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Site-Specific</Typography>
              <Typography variant="h4">
                {configurations.filter(c => c.is_site_specific).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Configurations Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Configuration</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Scope</TableCell>
              <TableCell>Version</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Modified</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {configurations.map((config) => (
              <TableRow key={config.id}>
                <TableCell>
                  <Box>
                    <Typography variant="body2" fontWeight="bold">
                      {config.config_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {config.config_key}
                    </Typography>
                    {config.config_description && (
                      <Typography variant="caption" color="text.secondary">
                        {config.config_description}
                      </Typography>
                    )}
                  </Box>
                </TableCell>
                <TableCell>
                  <Chip
                    label={config.config_type}
                    color={getTypeColor(config.config_type)}
                    size="small"
                    sx={{ textTransform: 'capitalize' }}
                  />
                </TableCell>
                <TableCell>
                  <Chip
                    label={config.config_scope}
                    color={getScopeColor(config.config_scope)}
                    size="small"
                    sx={{ textTransform: 'capitalize' }}
                  />
                  {config.site_id && (
                    <Typography variant="caption" display="block" color="text.secondary">
                      Site: {config.site_id}
                    </Typography>
                  )}
                  {config.user_id && (
                    <Typography variant="caption" display="block" color="text.secondary">
                      User: {config.user_id}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Typography variant="body2">v{config.version}</Typography>
                  {config.parent_config_id && (
                    <Tooltip title="Has revision history">
                      <HistoryIcon fontSize="small" color="action" />
                    </Tooltip>
                  )}
                </TableCell>
                <TableCell>
                  <Box display="flex" flexDirection="column" gap={0.5}>
                    <Chip
                      label={config.is_active ? 'Active' : 'Inactive'}
                      color={config.is_active ? 'success' : 'default'}
                      size="small"
                    />
                    {config.is_default && (
                      <Chip
                        label="Default"
                        color="primary"
                        size="small"
                      />
                    )}
                    <Chip
                      label={config.is_validated ? 'Validated' : 'Pending'}
                      color={config.is_validated ? 'success' : 'warning'}
                      size="small"
                    />
                  </Box>
                </TableCell>
                <TableCell>
                  <Typography variant="body2">
                    {new Date(config.updated_at).toLocaleDateString()}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    By: {config.modified_by || 'System'}
                  </Typography>
                </TableCell>
                <TableCell>
                  <Box display="flex" gap={1}>
                    <Tooltip title="View Configuration">
                      <IconButton
                        size="small"
                        onClick={() => handleViewConfig(config)}
                      >
                        <ViewIcon />
                      </IconButton>
                    </Tooltip>
                    {!config.is_validated && (
                      <Tooltip title="Validate Configuration">
                        <IconButton
                          size="small"
                          onClick={() => handleValidateConfig(config)}
                          color="primary"
                        >
                          <ValidateIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                    <Tooltip title="Export Configuration">
                      <IconButton
                        size="small"
                        onClick={() => handleExportConfig(config)}
                      >
                        <ExportIcon />
                      </IconButton>
                    </Tooltip>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* View Configuration Dialog */}
      <Dialog 
        open={viewDialogOpen} 
        onClose={() => setViewDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          Configuration Details: {selectedConfig?.config_name}
        </DialogTitle>
        <DialogContent>
          {selectedConfig && (
            <Box>
              {/* Configuration Metadata */}
              <Accordion defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">Metadata</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Grid container spacing={2}>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="body2" color="text.secondary">Key</Typography>
                      <Typography variant="body1">{selectedConfig.config_key}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="body2" color="text.secondary">Type</Typography>
                      <Typography variant="body1">{selectedConfig.config_type}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="body2" color="text.secondary">Scope</Typography>
                      <Typography variant="body1">{selectedConfig.config_scope}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="body2" color="text.secondary">Version</Typography>
                      <Typography variant="body1">v{selectedConfig.version}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="body2" color="text.secondary">Created By</Typography>
                      <Typography variant="body1">{selectedConfig.created_by || 'System'}</Typography>
                    </Grid>
                    <Grid item xs={12} sm={6}>
                      <Typography variant="body2" color="text.secondary">Modified By</Typography>
                      <Typography variant="body1">{selectedConfig.modified_by || 'System'}</Typography>
                    </Grid>
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">Description</Typography>
                      <Typography variant="body1">
                        {selectedConfig.config_description || 'No description provided'}
                      </Typography>
                    </Grid>
                    {selectedConfig.change_reason && (
                      <Grid item xs={12}>
                        <Typography variant="body2" color="text.secondary">Change Reason</Typography>
                        <Typography variant="body1">{selectedConfig.change_reason}</Typography>
                      </Grid>
                    )}
                  </Grid>
                </AccordionDetails>
              </Accordion>

              {/* Configuration Value */}
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="h6">Configuration Value</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <TextField
                    fullWidth
                    multiline
                    rows={20}
                    value={JSON.stringify(selectedConfig.config_value, null, 2)}
                    InputProps={{
                      readOnly: true,
                      style: { fontFamily: 'monospace', fontSize: '0.875rem' }
                    }}
                  />
                </AccordionDetails>
              </Accordion>

              {/* Validation Information */}
              {selectedConfig.is_validated && (
                <Accordion>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography variant="h6">Validation Information</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">Validated By</Typography>
                        <Typography variant="body1">{selectedConfig.validated_by}</Typography>
                      </Grid>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">Validation Date</Typography>
                        <Typography variant="body1">
                          {selectedConfig.validation_date 
                            ? new Date(selectedConfig.validation_date).toLocaleString()
                            : 'N/A'
                          }
                        </Typography>
                      </Grid>
                      {selectedConfig.validation_notes && (
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">Validation Notes</Typography>
                          <Typography variant="body1">{selectedConfig.validation_notes}</Typography>
                        </Grid>
                      )}
                    </Grid>
                  </AccordionDetails>
                </Accordion>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setViewDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>

      {/* Validate Configuration Dialog */}
      <Dialog 
        open={validateDialogOpen} 
        onClose={() => setValidateDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Validate Configuration: {selectedConfig?.config_name}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Validating this configuration will mark it as approved and ready for use.
            This action will perform validation checks and create an audit trail.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            label="Validation Notes (Optional)"
            value={validationNotes}
            onChange={(e) => setValidationNotes(e.target.value)}
            placeholder="Add any notes about the validation process or requirements..."
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setValidateDialogOpen(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleValidateSubmit}
            variant="contained"
            disabled={submitting}
          >
            {submitting ? 'Validating...' : 'Validate Configuration'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};