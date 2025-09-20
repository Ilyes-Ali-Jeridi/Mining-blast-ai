import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Grid,
  Alert,
  FormControlLabel,
  Switch,
  Accordion,
  AccordionSummary,
  AccordionDetails,
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
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { 
  OptimizationConstraints, 
  OptimizationObjectives, 
  Receptor, 
  Coordinates,
  FormValidationState 
} from '../../types';
import { createValidator } from '../../utils/validation';

interface ConstraintsObjectivesFormProps {
  constraints: Partial<OptimizationConstraints>;
  objectives: Partial<OptimizationObjectives>;
  onConstraintsChange: (constraints: Partial<OptimizationConstraints>) => void;
  onObjectivesChange: (objectives: Partial<OptimizationObjectives>) => void;
  onValidationChange?: (validation: FormValidationState) => void;
}

export const ConstraintsObjectivesForm: React.FC<ConstraintsObjectivesFormProps> = ({
  constraints,
  objectives,
  onConstraintsChange,
  onObjectivesChange,
  onValidationChange
}) => {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [warnings, setWarnings] = useState<Record<string, string>>({});
  const [receptorDialogOpen, setReceptorDialogOpen] = useState(false);
  const [editingReceptor, setEditingReceptor] = useState<Receptor | null>(null);
  const [receptorFormData, setReceptorFormData] = useState<Partial<Receptor>>({});

  // Validate forms whenever values change
  useEffect(() => {
    const validator = createValidator();
    
    // Validate constraints
    if (Object.keys(constraints).length > 0) {
      validator.validateOptimizationConstraints(constraints);
    }
    
    // Validate objectives
    if (Object.keys(objectives).length > 0) {
      validator.validateOptimizationObjectives(objectives);
    }
    
    const validationState = validator.getState();
    
    // Convert errors to field-keyed object for easy lookup
    const errorMap: Record<string, string> = {};
    const warningMap: Record<string, string> = {};
    
    validationState.errors.forEach(error => {
      errorMap[error.field] = error.message;
    });
    
    validationState.warnings.forEach(warning => {
      warningMap[warning.field] = warning.message;
    });
    
    setErrors(errorMap);
    setWarnings(warningMap);
    
    if (onValidationChange) {
      onValidationChange(validationState);
    }
  }, [JSON.stringify(constraints), JSON.stringify(objectives)]);

  const handleConstraintChange = (field: keyof OptimizationConstraints) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newValue = event.target.value;
    const numericValue = parseFloat(newValue);
    
    onConstraintsChange({
      ...constraints,
      [field]: isNaN(numericValue) ? newValue : numericValue
    });
  };

  const handleObjectiveChange = (field: keyof OptimizationObjectives) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newValue = event.target.value;
    let processedValue: any = newValue;
    
    if (field === 'minimize_oversize') {
      processedValue = event.target.checked;
    } else {
      const numericValue = parseFloat(newValue);
      processedValue = isNaN(numericValue) ? newValue : numericValue;
    }
    
    onObjectivesChange({
      ...objectives,
      [field]: processedValue
    });
  };

  const handleOpenReceptorDialog = (receptor?: Receptor) => {
    if (receptor) {
      setEditingReceptor(receptor);
      setReceptorFormData({ ...receptor });
    } else {
      setEditingReceptor(null);
      setReceptorFormData({
        id: '',
        name: '',
        coordinates: { x: 0, y: 0, z: 0 },
        ppv_limit: 5.0
      });
    }
    setReceptorDialogOpen(true);
  };

  const handleCloseReceptorDialog = () => {
    setReceptorDialogOpen(false);
    setEditingReceptor(null);
    setReceptorFormData({});
  };

  const handleSaveReceptor = () => {
    const newReceptor: Receptor = {
      ...receptorFormData as Receptor,
      id: editingReceptor?.id || `receptor_${Date.now()}`
    };
    
    const currentReceptors = constraints.sensitive_receptors || [];
    let updatedReceptors: Receptor[];
    
    if (editingReceptor) {
      updatedReceptors = currentReceptors.map(r => 
        r.id === editingReceptor.id ? newReceptor : r
      );
    } else {
      updatedReceptors = [...currentReceptors, newReceptor];
    }
    
    onConstraintsChange({
      ...constraints,
      sensitive_receptors: updatedReceptors
    });
    
    handleCloseReceptorDialog();
  };

  const handleDeleteReceptor = (id: string) => {
    const currentReceptors = constraints.sensitive_receptors || [];
    const updatedReceptors = currentReceptors.filter(r => r.id !== id);
    
    onConstraintsChange({
      ...constraints,
      sensitive_receptors: updatedReceptors
    });
  };

  const handleReceptorFieldChange = (field: string) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const value = event.target.value;
    
    if (field.startsWith('coordinates.')) {
      const coordField = field.split('.')[1] as keyof Coordinates;
      const numericValue = parseFloat(value);
      
      setReceptorFormData(prev => ({
        ...prev,
        coordinates: {
          ...prev.coordinates!,
          [coordField]: isNaN(numericValue) ? value : numericValue
        }
      }));
    } else {
      const processedValue = field === 'ppv_limit' ? parseFloat(value) : value;
      setReceptorFormData(prev => ({
        ...prev,
        [field]: processedValue
      }));
    }
  };

  const getFieldError = (field: string): string | undefined => {
    return errors[field];
  };

  return (
    <Box>
      {/* Constraints Section */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Optimization Constraints
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Minimum Burden (m)"
              type="number"
              value={constraints.min_burden || ''}
              onChange={handleConstraintChange('min_burden')}
              error={!!getFieldError('min_burden')}
              helperText={getFieldError('min_burden') || 'Minimum distance between holes and free face'}
              inputProps={{ min: 1, max: 20, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Maximum Burden (m)"
              type="number"
              value={constraints.max_burden || ''}
              onChange={handleConstraintChange('max_burden')}
              error={!!getFieldError('max_burden')}
              helperText={getFieldError('max_burden')}
              inputProps={{ min: 1, max: 20, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Minimum Spacing (m)"
              type="number"
              value={constraints.min_spacing || ''}
              onChange={handleConstraintChange('min_spacing')}
              error={!!getFieldError('min_spacing')}
              helperText={getFieldError('min_spacing') || 'Minimum distance between holes in a row'}
              inputProps={{ min: 1, max: 20, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Maximum Spacing (m)"
              type="number"
              value={constraints.max_spacing || ''}
              onChange={handleConstraintChange('max_spacing')}
              error={!!getFieldError('max_spacing')}
              helperText={getFieldError('max_spacing')}
              inputProps={{ min: 1, max: 20, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Minimum Powder Factor (kg/t)"
              type="number"
              value={constraints.powder_factor_min || ''}
              onChange={handleConstraintChange('powder_factor_min')}
              error={!!getFieldError('powder_factor_min')}
              helperText={getFieldError('powder_factor_min')}
              inputProps={{ min: 0.05, max: 2, step: 0.01 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Maximum Powder Factor (kg/t)"
              type="number"
              value={constraints.powder_factor_max || ''}
              onChange={handleConstraintChange('powder_factor_max')}
              error={!!getFieldError('powder_factor_max')}
              helperText={getFieldError('powder_factor_max')}
              inputProps={{ min: 0.05, max: 2, step: 0.01 }}
            />
          </Grid>
        </Grid>

        {/* Sensitive Receptors */}
        <Box sx={{ mt: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="subtitle1">
              Sensitive Receptors (PPV Monitoring Points)
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<AddIcon />}
              onClick={() => handleOpenReceptorDialog()}
            >
              Add Receptor
            </Button>
          </Box>
          
          {(!constraints.sensitive_receptors || constraints.sensitive_receptors.length === 0) ? (
            <Alert severity="info">
              No sensitive receptors defined. Add monitoring points where PPV limits must be enforced.
            </Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>X (m)</TableCell>
                    <TableCell>Y (m)</TableCell>
                    <TableCell>Z (m)</TableCell>
                    <TableCell>PPV Limit (mm/s)</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {constraints.sensitive_receptors.map((receptor) => (
                    <TableRow key={receptor.id}>
                      <TableCell>{receptor.name}</TableCell>
                      <TableCell>{receptor.coordinates.x}</TableCell>
                      <TableCell>{receptor.coordinates.y}</TableCell>
                      <TableCell>{receptor.coordinates.z}</TableCell>
                      <TableCell>{receptor.ppv_limit}</TableCell>
                      <TableCell>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenReceptorDialog(receptor)}
                        >
                          <EditIcon />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleDeleteReceptor(receptor.id)}
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
        </Box>
      </Paper>

      {/* Objectives Section */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Optimization Objectives
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Target P80 (mm)"
              type="number"
              value={objectives.target_p80 || ''}
              onChange={handleObjectiveChange('target_p80')}
              error={!!getFieldError('target_p80')}
              helperText={getFieldError('target_p80') || 'Target fragment size (80% passing)'}
              inputProps={{ min: 10, max: 1000, step: 1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Fragmentation Weight"
              type="number"
              value={objectives.weight_fragmentation || ''}
              onChange={handleObjectiveChange('weight_fragmentation')}
              error={!!getFieldError('weight_fragmentation')}
              helperText={getFieldError('weight_fragmentation') || 'Importance of achieving target fragmentation'}
              inputProps={{ min: 0, max: 10, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Cost Weight"
              type="number"
              value={objectives.weight_cost || ''}
              onChange={handleObjectiveChange('weight_cost')}
              error={!!getFieldError('weight_cost')}
              helperText={getFieldError('weight_cost') || 'Importance of minimizing costs'}
              inputProps={{ min: 0, max: 10, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="PPV Weight"
              type="number"
              value={objectives.weight_ppv || ''}
              onChange={handleObjectiveChange('weight_ppv')}
              error={!!getFieldError('weight_ppv')}
              helperText={getFieldError('weight_ppv') || 'Importance of minimizing vibration'}
              inputProps={{ min: 0, max: 10, step: 0.1 }}
            />
          </Grid>
          
          <Grid item xs={12}>
            <FormControlLabel
              control={
                <Switch
                  checked={objectives.minimize_oversize || false}
                  onChange={handleObjectiveChange('minimize_oversize')}
                />
              }
              label="Minimize Oversize Material"
            />
          </Grid>
        </Grid>
        
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            <strong>Weight Guidelines:</strong><br/>
            • Higher weights prioritize that objective more strongly<br/>
            • Fragmentation weight: Focus on achieving target P80<br/>
            • Cost weight: Minimize explosive usage and drilling<br/>
            • PPV weight: Stay well below vibration limits
          </Typography>
        </Box>
      </Paper>

      {/* Validation Alerts */}
      {Object.keys(errors).length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Please correct the validation errors above.
        </Alert>
      )}
      
      {Object.keys(warnings).length > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          Please review the warnings above.
        </Alert>
      )}

      {/* Receptor Dialog */}
      <Dialog open={receptorDialogOpen} onClose={handleCloseReceptorDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingReceptor ? 'Edit Receptor' : 'Add New Receptor'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Name"
                value={receptorFormData.name || ''}
                onChange={handleReceptorFieldChange('name')}
              />
            </Grid>
            
            <Grid item xs={4}>
              <TextField
                fullWidth
                label="X Coordinate (m)"
                type="number"
                value={receptorFormData.coordinates?.x || ''}
                onChange={handleReceptorFieldChange('coordinates.x')}
              />
            </Grid>
            
            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Y Coordinate (m)"
                type="number"
                value={receptorFormData.coordinates?.y || ''}
                onChange={handleReceptorFieldChange('coordinates.y')}
              />
            </Grid>
            
            <Grid item xs={4}>
              <TextField
                fullWidth
                label="Z Coordinate (m)"
                type="number"
                value={receptorFormData.coordinates?.z || ''}
                onChange={handleReceptorFieldChange('coordinates.z')}
              />
            </Grid>
            
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="PPV Limit (mm/s)"
                type="number"
                value={receptorFormData.ppv_limit || ''}
                onChange={handleReceptorFieldChange('ppv_limit')}
                inputProps={{ min: 0.1, max: 50, step: 0.1 }}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseReceptorDialog}>Cancel</Button>
          <Button onClick={handleSaveReceptor} variant="contained">
            {editingReceptor ? 'Update' : 'Add'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};