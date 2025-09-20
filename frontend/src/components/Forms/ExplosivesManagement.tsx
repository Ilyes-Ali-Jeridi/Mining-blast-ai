import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Grid,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { ExplosiveSpec, FormValidationState } from '../../types';
import { createValidator } from '../../utils/validation';

interface ExplosivesManagementProps {
  explosives: ExplosiveSpec[];
  onChange: (explosives: ExplosiveSpec[]) => void;
  onValidationChange?: (validation: FormValidationState) => void;
}

const EXPLOSIVE_TYPES: Array<ExplosiveSpec['type']> = ['ANFO', 'Emulsion', 'Slurry'];

export const ExplosivesManagement: React.FC<ExplosivesManagementProps> = ({
  explosives,
  onChange,
  onValidationChange
}) => {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingExplosive, setEditingExplosive] = useState<ExplosiveSpec | null>(null);
  const [formData, setFormData] = useState<Partial<ExplosiveSpec>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [overallValidation, setOverallValidation] = useState<FormValidationState>({
    isValid: true,
    errors: [],
    warnings: []
  });

  // Validate all explosives whenever the list changes
  useEffect(() => {
    const validator = createValidator();
    let allValid = true;
    
    explosives.forEach((explosive, index) => {
      if (!validator.validateExplosiveSpec(explosive)) {
        allValid = false;
      }
    });
    
    const validationState = validator.getState();
    setOverallValidation(validationState);
    
    if (onValidationChange) {
      onValidationChange(validationState);
    }
  }, [JSON.stringify(explosives)]);

  const handleOpenDialog = (explosive?: ExplosiveSpec) => {
    if (explosive) {
      setEditingExplosive(explosive);
      setFormData({ ...explosive });
    } else {
      setEditingExplosive(null);
      setFormData({
        name: '',
        type: 'ANFO',
        density: 800,
        rws: 100,
        vod: 4500,
        energy: 3.7,
        cost_per_kg: 1.0,
        regulatory_limit_per_hole: 50,
        regulatory_limit_per_delay: 200
      });
    }
    setErrors({});
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingExplosive(null);
    setFormData({});
    setErrors({});
  };

  const handleFieldChange = (field: keyof ExplosiveSpec) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newValue = event.target.value;
    let processedValue: any = newValue;
    
    // Convert numeric fields
    if (['density', 'rws', 'vod', 'energy', 'cost_per_kg', 'regulatory_limit_per_hole', 'regulatory_limit_per_delay'].includes(field)) {
      const numericValue = parseFloat(newValue);
      processedValue = isNaN(numericValue) ? newValue : numericValue;
    }
    
    setFormData(prev => ({
      ...prev,
      [field]: processedValue
    }));
  };

  const handleSelectChange = (field: keyof ExplosiveSpec) => (
    event: any
  ) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  const handleSave = () => {
    const validator = createValidator();
    const isValid = validator.validateExplosiveSpec(formData);
    const validationState = validator.getState();
    
    if (!isValid) {
      const errorMap: Record<string, string> = {};
      validationState.errors.forEach(error => {
        errorMap[error.field] = error.message;
      });
      setErrors(errorMap);
      return;
    }
    
    const newExplosive: ExplosiveSpec = {
      ...formData as ExplosiveSpec,
      id: editingExplosive?.id || Date.now()
    };
    
    let updatedExplosives: ExplosiveSpec[];
    if (editingExplosive) {
      updatedExplosives = explosives.map(exp => 
        exp.id === editingExplosive.id ? newExplosive : exp
      );
    } else {
      updatedExplosives = [...explosives, newExplosive];
    }
    
    onChange(updatedExplosives);
    handleCloseDialog();
  };

  const handleDelete = (id: number) => {
    const updatedExplosives = explosives.filter(exp => exp.id !== id);
    onChange(updatedExplosives);
  };

  const getFieldError = (field: string): string | undefined => {
    return errors[field];
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Explosives Database
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenDialog()}
        >
          Add Explosive
        </Button>
      </Box>
      
      {explosives.length === 0 ? (
        <Alert severity="info">
          No explosives configured. Add at least one explosive type to proceed.
        </Alert>
      ) : (
        <TableContainer>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Name</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Density (kg/m³)</TableCell>
                <TableCell>RWS (%)</TableCell>
                <TableCell>VOD (m/s)</TableCell>
                <TableCell>Cost ($/kg)</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {explosives.map((explosive) => (
                <TableRow key={explosive.id}>
                  <TableCell>{explosive.name}</TableCell>
                  <TableCell>
                    <Chip 
                      label={explosive.type} 
                      size="small"
                      color={explosive.type === 'ANFO' ? 'primary' : explosive.type === 'Emulsion' ? 'secondary' : 'default'}
                    />
                  </TableCell>
                  <TableCell>{explosive.density}</TableCell>
                  <TableCell>{explosive.rws}</TableCell>
                  <TableCell>{explosive.vod}</TableCell>
                  <TableCell>${explosive.cost_per_kg.toFixed(2)}</TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      onClick={() => handleOpenDialog(explosive)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(explosive.id!)}
                      color="error"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
      
      {!overallValidation.isValid && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Some explosives have validation errors. Please review and correct them.
        </Alert>
      )}

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingExplosive ? 'Edit Explosive' : 'Add New Explosive'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Name"
                value={formData.name || ''}
                onChange={handleFieldChange('name')}
                error={!!getFieldError('name')}
                helperText={getFieldError('name')}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <FormControl fullWidth error={!!getFieldError('type')}>
                <InputLabel>Type</InputLabel>
                <Select
                  value={formData.type || 'ANFO'}
                  onChange={handleSelectChange('type')}
                  label="Type"
                >
                  {EXPLOSIVE_TYPES.map((type) => (
                    <MenuItem key={type} value={type}>
                      {type}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Density (kg/m³)"
                type="number"
                value={formData.density || ''}
                onChange={handleFieldChange('density')}
                error={!!getFieldError('density')}
                helperText={getFieldError('density')}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="RWS - Relative Weight Strength (%)"
                type="number"
                value={formData.rws || ''}
                onChange={handleFieldChange('rws')}
                error={!!getFieldError('rws')}
                helperText={getFieldError('rws')}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="VOD - Velocity of Detonation (m/s)"
                type="number"
                value={formData.vod || ''}
                onChange={handleFieldChange('vod')}
                error={!!getFieldError('vod')}
                helperText={getFieldError('vod')}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Energy (MJ/kg)"
                type="number"
                value={formData.energy || ''}
                onChange={handleFieldChange('energy')}
                error={!!getFieldError('energy')}
                helperText={getFieldError('energy')}
                inputProps={{ step: 0.1 }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Cost per kg ($)"
                type="number"
                value={formData.cost_per_kg || ''}
                onChange={handleFieldChange('cost_per_kg')}
                error={!!getFieldError('cost_per_kg')}
                helperText={getFieldError('cost_per_kg')}
                inputProps={{ step: 0.01 }}
              />
            </Grid>
            
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="Regulatory Limit per Hole (kg)"
                type="number"
                value={formData.regulatory_limit_per_hole || ''}
                onChange={handleFieldChange('regulatory_limit_per_hole')}
                error={!!getFieldError('regulatory_limit_per_hole')}
                helperText={getFieldError('regulatory_limit_per_hole')}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Regulatory Limit per Delay (kg)"
                type="number"
                value={formData.regulatory_limit_per_delay || ''}
                onChange={handleFieldChange('regulatory_limit_per_delay')}
                error={!!getFieldError('regulatory_limit_per_delay')}
                helperText={getFieldError('regulatory_limit_per_delay')}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSave} variant="contained">
            {editingExplosive ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};