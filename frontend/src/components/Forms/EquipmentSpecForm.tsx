import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Grid,
  Alert,
} from '@mui/material';
import { DrillRigSpec, FormValidationState } from '../../types';
import { createValidator } from '../../utils/validation';

interface EquipmentSpecFormProps {
  value: Partial<DrillRigSpec>;
  onChange: (spec: Partial<DrillRigSpec>) => void;
  onValidationChange?: (validation: FormValidationState) => void;
}

export const EquipmentSpecForm: React.FC<EquipmentSpecFormProps> = ({
  value,
  onChange,
  onValidationChange
}) => {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [warnings, setWarnings] = useState<Record<string, string>>({});

  // Validate form whenever value changes
  useEffect(() => {
    const validator = createValidator();
    const isValid = validator.validateDrillRigSpec(value);
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
  }, [JSON.stringify(value)]);

  const handleFieldChange = (field: keyof DrillRigSpec) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newValue = event.target.value;
    const numericValue = parseFloat(newValue);
    
    onChange({
      ...value,
      [field]: isNaN(numericValue) ? newValue : numericValue
    });
  };

  const getFieldError = (field: string): string | undefined => {
    return errors[field];
  };

  const getFieldWarning = (field: string): string | undefined => {
    return warnings[field];
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Drill Rig Specifications
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Drill Rig Name"
            type="text"
            value={value.name || ''}
            onChange={handleFieldChange('name')}
            error={!!getFieldError('name')}
            helperText={getFieldError('name') || 'Name or model of the drill rig'}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Operating Cost ($/hour)"
            type="number"
            value={value.operating_cost || ''}
            onChange={handleFieldChange('operating_cost')}
            error={!!getFieldError('operating_cost')}
            helperText={getFieldError('operating_cost') || 'Hourly operating cost including fuel, maintenance, operator'}
            inputProps={{ min: 0, step: 0.01 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Maximum Hole Diameter (mm)"
            type="number"
            value={value.max_hole_diameter || ''}
            onChange={handleFieldChange('max_hole_diameter')}
            error={!!getFieldError('max_hole_diameter')}
            helperText={getFieldError('max_hole_diameter') || 'Typical range: 50-500 mm'}
            inputProps={{ min: 50, max: 500, step: 1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Maximum Depth (m)"
            type="number"
            value={value.max_depth || ''}
            onChange={handleFieldChange('max_depth')}
            error={!!getFieldError('max_depth')}
            helperText={getFieldError('max_depth') || 'Maximum drilling depth capability'}
            inputProps={{ min: 1, max: 50, step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Collar Accuracy (m)"
            type="number"
            value={value.collar_accuracy || ''}
            onChange={handleFieldChange('collar_accuracy')}
            error={!!getFieldError('collar_accuracy')}
            helperText={getFieldError('collar_accuracy') || 'Positioning accuracy at surface'}
            inputProps={{ min: 0.01, max: 1, step: 0.01 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Drilling Rate (m/hr)"
            type="number"
            value={value.drilling_rate || ''}
            onChange={handleFieldChange('drilling_rate')}
            error={!!getFieldError('drilling_rate')}
            helperText={getFieldError('drilling_rate') || 'Average drilling speed'}
            inputProps={{ min: 1, max: 100, step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Setup Time (minutes)"
            type="number"
            value={value.setup_time || ''}
            onChange={handleFieldChange('setup_time')}
            error={!!getFieldError('setup_time')}
            helperText={getFieldError('setup_time') || 'Time to position and setup rig'}
            inputProps={{ min: 1, max: 120, step: 1 }}
          />
        </Grid>
      </Grid>
      
      <Box sx={{ mt: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Equipment Guidelines:</strong><br/>
          • Hole diameter affects charge capacity and fragmentation<br/>
          • Collar accuracy impacts blast pattern precision<br/>
          • Drilling rate and setup time affect operational costs
        </Typography>
      </Box>
      
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
    </Paper>
  );
};