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
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  LocalFireDepartment as ExplosiveIcon,
  Science as ScienceIcon,
  AttachMoney as CostIcon,
  Security as SafetyIcon
} from '@mui/icons-material';

import { adminService, ExplosiveSpec, ExplosivesCatalog } from '../../services/adminService';

interface ExplosiveFormData {
  id: string;
  name: string;
  manufacturer: string;
  type: string;
  density: number;
  rws: number;
  vod: number;
  energy: number;
  cost_per_kg: number;
  availability: {
    regions: string[];
    lead_time_days: number;
    minimum_order: number;
  };
  regulatory: {
    max_per_hole: number;
    max_per_delay: number;
    storage_class: string;
    transport_class: string;
  };
  performance: {
    temperature_range: [number, number];
    water_resistance: string;
    fume_class: number;
    sensitivity: string;
  };
  is_active: boolean;
}

const initialFormData: ExplosiveFormData = {
  id: '',
  name: '',
  manufacturer: '',
  type: 'ANFO',
  density: 850,
  rws: 100,
  vod: 4500,
  energy: 3.7,
  cost_per_kg: 1.50,
  availability: {
    regions: ['global'],
    lead_time_days: 7,
    minimum_order: 1000
  },
  regulatory: {
    max_per_hole: 50,
    max_per_delay: 200,
    storage_class: '1.1D',
    transport_class: '1.1D'
  },
  performance: {
    temperature_range: [-10, 50],
    water_resistance: 'good',
    fume_class: 2,
    sensitivity: 'medium'
  },
  is_active: true
};

export const ExplosivesManager: React.FC = () => {
  const [catalog, setCatalog] = useState<ExplosivesCatalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingExplosive, setEditingExplosive] = useState<ExplosiveSpec | null>(null);
  const [formData, setFormData] = useState<ExplosiveFormData>(initialFormData);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [includeInactive, setIncludeInactive] = useState(false);

  useEffect(() => {
    loadCatalog();
  }, [includeInactive]);

  const loadCatalog = async () => {
    try {
      setLoading(true);
      const catalogData = await adminService.getExplosivesCatalog(includeInactive);
      setCatalog(catalogData);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load explosives catalog:', err);
      setError(err.message || 'Failed to load explosives catalog');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateExplosive = () => {
    setEditingExplosive(null);
    setFormData({
      ...initialFormData,
      id: `explosive_${Date.now()}`
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const handleEditExplosive = (explosive: ExplosiveSpec) => {
    setEditingExplosive(explosive);
    setFormData({
      id: explosive.id,
      name: explosive.name,
      manufacturer: explosive.manufacturer,
      type: explosive.type,
      density: explosive.density,
      rws: explosive.rws,
      vod: explosive.vod,
      energy: explosive.energy,
      cost_per_kg: explosive.cost_per_kg,
      availability: explosive.availability || initialFormData.availability,
      regulatory: explosive.regulatory || initialFormData.regulatory,
      performance: explosive.performance || initialFormData.performance,
      is_active: explosive.is_active
    });
    setFormErrors({});
    setDialogOpen(true);
  };

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (!formData.id.trim()) {
      errors.id = 'ID is required';
    }

    if (!formData.name.trim()) {
      errors.name = 'Name is required';
    }

    if (!formData.manufacturer.trim()) {
      errors.manufacturer = 'Manufacturer is required';
    }

    if (formData.density <= 0) {
      errors.density = 'Density must be positive';
    }

    if (formData.rws <= 0) {
      errors.rws = 'RWS must be positive';
    }

    if (formData.vod <= 0) {
      errors.vod = 'VOD must be positive';
    }

    if (formData.energy <= 0) {
      errors.energy = 'Energy must be positive';
    }

    if (formData.cost_per_kg < 0) {
      errors.cost_per_kg = 'Cost cannot be negative';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    if (!catalog) {
      setError('No catalog loaded');
      return;
    }

    setSubmitting(true);
    try {
      const updatedExplosives = [...catalog.explosives];
      
      if (editingExplosive) {
        // Update existing explosive
        const index = updatedExplosives.findIndex(e => e.id === editingExplosive.id);
        if (index >= 0) {
          updatedExplosives[index] = formData as ExplosiveSpec;
        }
      } else {
        // Add new explosive
        updatedExplosives.push(formData as ExplosiveSpec);
      }

      await adminService.updateExplosivesCatalog({
        explosives: updatedExplosives
      });

      setDialogOpen(false);
      await loadCatalog();
    } catch (err: any) {
      console.error('Failed to save explosive:', err);
      setError(err.message || 'Failed to save explosive');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteExplosive = async (explosive: ExplosiveSpec) => {
    if (!catalog) return;

    if (!confirm(`Are you sure you want to delete "${explosive.name}"?`)) {
      return;
    }

    try {
      const updatedExplosives = catalog.explosives.filter(e => e.id !== explosive.id);
      
      await adminService.updateExplosivesCatalog({
        explosives: updatedExplosives
      });

      await loadCatalog();
    } catch (err: any) {
      console.error('Failed to delete explosive:', err);
      setError(err.message || 'Failed to delete explosive');
    }
  };

  const getTypeColor = (type: string): 'primary' | 'secondary' | 'success' | 'warning' => {
    switch (type.toLowerCase()) {
      case 'anfo':
        return 'primary';
      case 'emulsion':
        return 'success';
      case 'slurry':
        return 'warning';
      default:
        return 'secondary';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading explosives catalog...</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Explosives Database Management
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <FormControlLabel
            control={
              <Switch
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
            }
            label="Include Inactive"
          />
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleCreateExplosive}
          >
            Add Explosive
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Catalog Statistics */}
      {catalog && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1}>
                  <ExplosiveIcon color="primary" />
                  <Typography variant="h6">Total Explosives</Typography>
                </Box>
                <Typography variant="h4">{catalog.metadata.total_explosives}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1}>
                  <ScienceIcon color="success" />
                  <Typography variant="h6">Active</Typography>
                </Box>
                <Typography variant="h4">{catalog.metadata.active_explosives}</Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Last Updated</Typography>
                <Typography variant="body2" color="text.secondary">
                  {catalog.metadata.last_updated 
                    ? new Date(catalog.metadata.last_updated).toLocaleDateString()
                    : 'Never'
                  }
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  By: {catalog.metadata.updated_by || 'System'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Version</Typography>
                <Typography variant="h4">{catalog.metadata.version || 1}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Explosives Table */}
      {catalog && (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Explosive</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Properties</TableCell>
                <TableCell>Regulatory Limits</TableCell>
                <TableCell>Cost</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {catalog.explosives.map((explosive) => (
                <TableRow key={explosive.id}>
                  <TableCell>
                    <Box>
                      <Typography variant="body2" fontWeight="bold">
                        {explosive.name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {explosive.manufacturer}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        ID: {explosive.id}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={explosive.type}
                      color={getTypeColor(explosive.type)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Typography variant="body2">
                        Density: {explosive.density} kg/m³
                      </Typography>
                      <Typography variant="body2">
                        RWS: {explosive.rws}%
                      </Typography>
                      <Typography variant="body2">
                        VOD: {explosive.vod} m/s
                      </Typography>
                      <Typography variant="body2">
                        Energy: {explosive.energy} MJ/kg
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box>
                      <Typography variant="body2">
                        Max/hole: {explosive.regulatory?.max_per_hole || 'N/A'} kg
                      </Typography>
                      <Typography variant="body2">
                        Max/delay: {explosive.regulatory?.max_per_delay || 'N/A'} kg
                      </Typography>
                      <Typography variant="body2">
                        Class: {explosive.regulatory?.storage_class || 'N/A'}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      ${explosive.cost_per_kg.toFixed(2)}/kg
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={explosive.is_active ? 'Active' : 'Inactive'}
                      color={explosive.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={1}>
                      <Tooltip title="Edit Explosive">
                        <IconButton
                          size="small"
                          onClick={() => handleEditExplosive(explosive)}
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete Explosive">
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteExplosive(explosive)}
                          color="error"
                        >
                          <DeleteIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Explosive Form Dialog */}
      <Dialog 
        open={dialogOpen} 
        onClose={() => setDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>
          {editingExplosive ? 'Edit Explosive' : 'Add New Explosive'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            {/* Basic Information */}
            <Accordion defaultExpanded>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Basic Information</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="ID"
                      value={formData.id}
                      onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                      error={!!formErrors.id}
                      helperText={formErrors.id}
                      disabled={!!editingExplosive}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Name"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      error={!!formErrors.name}
                      helperText={formErrors.name}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Manufacturer"
                      value={formData.manufacturer}
                      onChange={(e) => setFormData({ ...formData, manufacturer: e.target.value })}
                      error={!!formErrors.manufacturer}
                      helperText={formErrors.manufacturer}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <FormControl fullWidth>
                      <InputLabel>Type</InputLabel>
                      <Select
                        value={formData.type}
                        label="Type"
                        onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                      >
                        <MenuItem value="ANFO">ANFO</MenuItem>
                        <MenuItem value="Emulsion">Emulsion</MenuItem>
                        <MenuItem value="Slurry">Slurry</MenuItem>
                        <MenuItem value="Gel">Gel</MenuItem>
                        <MenuItem value="Powder">Powder</MenuItem>
                        <MenuItem value="Other">Other</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            {/* Physical Properties */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Physical Properties</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Density (kg/m³)"
                      type="number"
                      value={formData.density}
                      onChange={(e) => setFormData({ ...formData, density: parseFloat(e.target.value) || 0 })}
                      error={!!formErrors.density}
                      helperText={formErrors.density}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="RWS (%)"
                      type="number"
                      value={formData.rws}
                      onChange={(e) => setFormData({ ...formData, rws: parseFloat(e.target.value) || 0 })}
                      error={!!formErrors.rws}
                      helperText={formErrors.rws}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="VOD (m/s)"
                      type="number"
                      value={formData.vod}
                      onChange={(e) => setFormData({ ...formData, vod: parseFloat(e.target.value) || 0 })}
                      error={!!formErrors.vod}
                      helperText={formErrors.vod}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Energy (MJ/kg)"
                      type="number"
                      step="0.1"
                      value={formData.energy}
                      onChange={(e) => setFormData({ ...formData, energy: parseFloat(e.target.value) || 0 })}
                      error={!!formErrors.energy}
                      helperText={formErrors.energy}
                    />
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            {/* Regulatory Information */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Regulatory Limits</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Max per Hole (kg)"
                      type="number"
                      value={formData.regulatory.max_per_hole}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        regulatory: { 
                          ...formData.regulatory, 
                          max_per_hole: parseFloat(e.target.value) || 0 
                        }
                      })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Max per Delay (kg)"
                      type="number"
                      value={formData.regulatory.max_per_delay}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        regulatory: { 
                          ...formData.regulatory, 
                          max_per_delay: parseFloat(e.target.value) || 0 
                        }
                      })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Storage Class"
                      value={formData.regulatory.storage_class}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        regulatory: { 
                          ...formData.regulatory, 
                          storage_class: e.target.value 
                        }
                      })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Transport Class"
                      value={formData.regulatory.transport_class}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        regulatory: { 
                          ...formData.regulatory, 
                          transport_class: e.target.value 
                        }
                      })}
                    />
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>

            {/* Cost and Availability */}
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography variant="h6">Cost and Availability</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="Cost per kg ($)"
                      type="number"
                      step="0.01"
                      value={formData.cost_per_kg}
                      onChange={(e) => setFormData({ ...formData, cost_per_kg: parseFloat(e.target.value) || 0 })}
                      error={!!formErrors.cost_per_kg}
                      helperText={formErrors.cost_per_kg}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="Lead Time (days)"
                      type="number"
                      value={formData.availability.lead_time_days}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        availability: { 
                          ...formData.availability, 
                          lead_time_days: parseInt(e.target.value) || 0 
                        }
                      })}
                    />
                  </Grid>
                  <Grid item xs={12} sm={4}>
                    <TextField
                      fullWidth
                      label="Minimum Order (kg)"
                      type="number"
                      value={formData.availability.minimum_order}
                      onChange={(e) => setFormData({ 
                        ...formData, 
                        availability: { 
                          ...formData.availability, 
                          minimum_order: parseFloat(e.target.value) || 0 
                        }
                      })}
                    />
                  </Grid>
                  <Grid item xs={12}>
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
                </Grid>
              </AccordionDetails>
            </Accordion>
          </Box>
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
            {submitting ? 'Saving...' : (editingExplosive ? 'Update' : 'Add')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};