import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Grid,
  Alert,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
} from '@mui/material';
import { RockProperties, FormValidationState } from '../../types';
import { createValidator } from '../../utils/validation';

interface RockPropertiesFormProps {
  value: Partial<RockProperties>;
  onChange: (properties: Partial<RockProperties>) => void;
  onValidationChange?: (validation: FormValidationState) => void;
}

const ROCK_TYPES = [
  'Granite',
  'Limestone',
  'Sandstone',
  'Basalt',
  'Quartzite',
  'Shale',
  'Dolomite',
  'Andesite',
  'Gneiss',
  'Schist',
  'Other'
];

export const RockPropertiesForm: React.FC<RockPropertiesFormProps> = ({
  value,
  onChange,
  onValidationChange
}) => {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [warnings, setWarnings] = useState<Record<string, string>>({});

  // Validate form whenever value changes
  useEffect(() => {
    const validator = createValidator();
    const isValid = validator.validateRockProperties(value);
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

  const handleFieldChange = (field: keyof RockProperties) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const newValue = event.target.value;
    let processedValue: any = newValue;
    
    // Convert numeric fields
    if (['ucs', 'density', 'rock_factor_a', 'grade'].includes(field)) {
      const numericValue = parseFloat(newValue);
      processedValue = isNaN(numericValue) ? newValue : numericValue;
    }
    
    onChange({
      ...value,
      [field]: processedValue
    });
  };

  const handleSelectChange = (field: keyof RockProperties) => (
    event: any
  ) => {
    onChange({
      ...value,
      [field]: event.target.value
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
        Rock Properties
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <FormControl fullWidth error={!!getFieldError('rock_type')}>
            <InputLabel>Rock Type</InputLabel>
            <Select
              value={value.rock_type || ''}
              onChange={handleSelectChange('rock_type')}
              label="Rock Type"
            >
              {ROCK_TYPES.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
            {getFieldError('rock_type') && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                {getFieldError('rock_type')}
              </Typography>
            )}
          </FormControl>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="UCS - Unconfined Compressive Strength (MPa)"
            type="number"
            value={value.ucs || ''}
            onChange={handleFieldChange('ucs')}
            error={!!getFieldError('ucs')}
            helperText={getFieldError('ucs') || 'Typical range: 1-500 MPa'}
            inputProps={{ min: 1, max: 500, step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Density (kg/m³)"
            type="number"
            value={value.density || ''}
            onChange={handleFieldChange('density')}
            error={!!getFieldError('density')}
            helperText={getFieldError('density') || 'Typical range: 1000-5000 kg/m³'}
            inputProps={{ min: 1000, max: 5000, step: 1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Rock Factor A (Kuz-Ram)"
            type="number"
            value={value.rock_factor_a || 7.0}
            onChange={handleFieldChange('rock_factor_a')}
            error={!!getFieldError('rock_factor_a')}
            helperText={getFieldError('rock_factor_a') || 'Default: 7.0, Range: 1-20'}
            inputProps={{ min: 1, max: 20, step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Grade (% - Optional)"
            type="number"
            value={value.grade || ''}
            onChange={handleFieldChange('grade')}
            error={!!getFieldError('grade')}
            helperText={getFieldError('grade') || 'Optional ore grade percentage'}
            inputProps={{ min: 0, max: 100, step: 0.01 }}
          />
        </Grid>
      </Grid>
      
      <Box sx={{ mt: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Rock Factor A Guidelines:</strong><br/>
          • Very hard, massive rock (granite, quartzite): 6-8<br/>
          • Medium hard rock (limestone, sandstone): 8-12<br/>
          • Soft, fractured rock (shale, weathered rock): 12-20
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