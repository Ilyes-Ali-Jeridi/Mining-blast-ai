import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Typography,
  Paper,
  Grid,
  Alert,
  FormHelperText,
} from '@mui/material';
import { BenchGeometry, ValidationError, FormValidationState } from '../../types';
import { createValidator } from '../../utils/validation';

interface SiteGeometryFormProps {
  value: Partial<BenchGeometry>;
  onChange: (geometry: Partial<BenchGeometry>) => void;
  onValidationChange?: (validation: FormValidationState) => void;
}

export const SiteGeometryForm: React.FC<SiteGeometryFormProps> = ({
  value,
  onChange,
  onValidationChange
}) => {
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [warnings, setWarnings] = useState<Record<string, string>>({});

  // Validate form whenever value changes
  useEffect(() => {
    const validator = createValidator();
    const isValid = validator.validateBenchGeometry(value);
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

  const handleFieldChange = (field: keyof BenchGeometry) => (
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
        Site Geometry
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Bench Top Elevation (m)"
            type="number"
            value={value.bench_top_elevation || ''}
            onChange={handleFieldChange('bench_top_elevation')}
            error={!!getFieldError('bench_top_elevation')}
            helperText={getFieldError('bench_top_elevation')}
            inputProps={{ step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Bench Bottom Elevation (m)"
            type="number"
            value={value.bench_bottom_elevation || ''}
            onChange={handleFieldChange('bench_bottom_elevation')}
            error={!!getFieldError('bench_bottom_elevation')}
            helperText={getFieldError('bench_bottom_elevation')}
            inputProps={{ step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Free Face Orientation (degrees)"
            type="number"
            value={value.free_face_orientation || ''}
            onChange={handleFieldChange('free_face_orientation')}
            error={!!getFieldError('free_face_orientation')}
            helperText={getFieldError('free_face_orientation') || 'Angle from north (0-360°)'}
            inputProps={{ min: 0, max: 360, step: 1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Bench Width (m)"
            type="number"
            value={value.bench_width || ''}
            onChange={handleFieldChange('bench_width')}
            error={!!getFieldError('bench_width')}
            helperText={getFieldError('bench_width')}
            inputProps={{ min: 0, step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12} md={6}>
          <TextField
            fullWidth
            label="Bench Length (m)"
            type="number"
            value={value.bench_length || ''}
            onChange={handleFieldChange('bench_length')}
            error={!!getFieldError('bench_length')}
            helperText={getFieldError('bench_length')}
            inputProps={{ min: 0, step: 0.1 }}
          />
        </Grid>
        
        <Grid item xs={12}>
          <Box sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Topography mesh data can be uploaded separately after site creation.
            </Typography>
          </Box>
        </Grid>
      </Grid>
      
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