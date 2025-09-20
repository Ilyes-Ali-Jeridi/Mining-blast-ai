import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Slider,
  Button,
  Grid,
  Divider,
  Alert,
  Select,
  MenuItem,
  InputLabel,
  Chip,
  Stack
} from '@mui/material';
import { OptimizationConfig } from '../../types';

interface OptimizationConfigProps {
  config: OptimizationConfig;
  onChange: (config: OptimizationConfig) => void;
  onSavePreset?: (name: string, config: OptimizationConfig) => void;
  presets?: Array<{ id: number; name: string; config: OptimizationConfig }>;
  onLoadPreset?: (config: OptimizationConfig) => void;
}

const defaultConfig: OptimizationConfig = {
  algorithms: ['cp_sat', 'scipy_de'],
  max_iterations: 1000,
  timeout_seconds: 300,
  convergence_tolerance: 1e-6,
  population_size: 50,
  mutation_rate: 0.1,
  crossover_rate: 0.8
};

const availableAlgorithms = [
  { value: 'cp_sat', label: 'CP-SAT (Constraint Programming)', description: 'Best for discrete optimization' },
  { value: 'scipy_de', label: 'Differential Evolution', description: 'Global optimization for continuous variables' },
  { value: 'scipy_slsqp', label: 'SLSQP', description: 'Sequential quadratic programming' },
  { value: 'genetic', label: 'Genetic Algorithm', description: 'Evolutionary optimization' }
];

export const OptimizationConfigComponent: React.FC<OptimizationConfigProps> = ({
  config,
  onChange,
  onSavePreset,
  presets = [],
  onLoadPreset
}) => {
  const [localConfig, setLocalConfig] = useState<OptimizationConfig>(config);
  const [presetName, setPresetName] = useState('');
  const [showPresetSave, setShowPresetSave] = useState(false);

  useEffect(() => {
    setLocalConfig(config);
  }, [config]);

  const handleConfigChange = (updates: Partial<OptimizationConfig>) => {
    const newConfig = { ...localConfig, ...updates };
    setLocalConfig(newConfig);
    onChange(newConfig);
  };

  const handleAlgorithmToggle = (algorithm: string) => {
    const newAlgorithms = localConfig.algorithms.includes(algorithm)
      ? localConfig.algorithms.filter(a => a !== algorithm)
      : [...localConfig.algorithms, algorithm];
    
    handleConfigChange({ algorithms: newAlgorithms });
  };

  const handleSavePreset = () => {
    if (presetName.trim() && onSavePreset) {
      onSavePreset(presetName.trim(), localConfig);
      setPresetName('');
      setShowPresetSave(false);
    }
  };

  const handleLoadPreset = (presetConfig: OptimizationConfig) => {
    setLocalConfig(presetConfig);
    onChange(presetConfig);
    if (onLoadPreset) {
      onLoadPreset(presetConfig);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Optimization Configuration
        </Typography>

        {/* Preset Management */}
        {presets.length > 0 && (
          <Box mb={3}>
            <Typography variant="subtitle2" gutterBottom>
              Configuration Presets
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {presets.map((preset) => (
                <Chip
                  key={preset.id}
                  label={preset.name}
                  onClick={() => handleLoadPreset(preset.config)}
                  variant="outlined"
                  size="small"
                />
              ))}
            </Stack>
          </Box>
        )}

        <Grid container spacing={3}>
          {/* Algorithm Selection */}
          <Grid item xs={12}>
            <FormControl component="fieldset">
              <FormLabel component="legend">
                <Typography variant="subtitle2">Optimization Algorithms</Typography>
              </FormLabel>
              <FormGroup>
                {availableAlgorithms.map((algorithm) => (
                  <Box key={algorithm.value} mb={1}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={localConfig.algorithms.includes(algorithm.value)}
                          onChange={() => handleAlgorithmToggle(algorithm.value)}
                        />
                      }
                      label={
                        <Box>
                          <Typography variant="body2" fontWeight="medium">
                            {algorithm.label}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {algorithm.description}
                          </Typography>
                        </Box>
                      }
                    />
                  </Box>
                ))}
              </FormGroup>
            </FormControl>
            
            {localConfig.algorithms.length === 0 && (
              <Alert severity="warning" sx={{ mt: 1 }}>
                Please select at least one optimization algorithm.
              </Alert>
            )}
          </Grid>

          <Grid item xs={12}>
            <Divider />
          </Grid>

          {/* General Parameters */}
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Maximum Iterations"
              type="number"
              value={localConfig.max_iterations || ''}
              onChange={(e) => handleConfigChange({ 
                max_iterations: parseInt(e.target.value) || undefined 
              })}
              helperText="Maximum number of iterations per algorithm"
              inputProps={{ min: 1, max: 10000 }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Timeout (seconds)"
              type="number"
              value={localConfig.timeout_seconds || ''}
              onChange={(e) => handleConfigChange({ 
                timeout_seconds: parseInt(e.target.value) || undefined 
              })}
              helperText="Maximum optimization time"
              inputProps={{ min: 10, max: 3600 }}
            />
          </Grid>

          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label="Convergence Tolerance"
              type="number"
              value={localConfig.convergence_tolerance || ''}
              onChange={(e) => handleConfigChange({ 
                convergence_tolerance: parseFloat(e.target.value) || undefined 
              })}
              helperText="Optimization convergence criteria"
              inputProps={{ min: 1e-10, max: 1e-2, step: 1e-6 }}
            />
          </Grid>

          {/* Genetic Algorithm Parameters */}
          {localConfig.algorithms.includes('genetic') && (
            <>
              <Grid item xs={12}>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  Genetic Algorithm Parameters
                </Typography>
              </Grid>

              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Population Size"
                  type="number"
                  value={localConfig.population_size || ''}
                  onChange={(e) => handleConfigChange({ 
                    population_size: parseInt(e.target.value) || undefined 
                  })}
                  helperText="Number of individuals in population"
                  inputProps={{ min: 10, max: 500 }}
                />
              </Grid>

              <Grid item xs={12} md={4}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Mutation Rate: {(localConfig.mutation_rate || 0.1).toFixed(2)}
                  </Typography>
                  <Slider
                    value={localConfig.mutation_rate || 0.1}
                    onChange={(_, value) => handleConfigChange({ 
                      mutation_rate: value as number 
                    })}
                    min={0.01}
                    max={0.5}
                    step={0.01}
                    valueLabelDisplay="auto"
                  />
                </Box>
              </Grid>

              <Grid item xs={12} md={4}>
                <Box>
                  <Typography variant="body2" gutterBottom>
                    Crossover Rate: {(localConfig.crossover_rate || 0.8).toFixed(2)}
                  </Typography>
                  <Slider
                    value={localConfig.crossover_rate || 0.8}
                    onChange={(_, value) => handleConfigChange({ 
                      crossover_rate: value as number 
                    })}
                    min={0.1}
                    max={1.0}
                    step={0.01}
                    valueLabelDisplay="auto"
                  />
                </Box>
              </Grid>
            </>
          )}

          {/* Preset Save */}
          <Grid item xs={12}>
            <Divider />
            <Box mt={2}>
              {!showPresetSave ? (
                <Button
                  variant="outlined"
                  onClick={() => setShowPresetSave(true)}
                  disabled={!onSavePreset}
                >
                  Save as Preset
                </Button>
              ) : (
                <Box display="flex" gap={1} alignItems="center">
                  <TextField
                    size="small"
                    label="Preset Name"
                    value={presetName}
                    onChange={(e) => setPresetName(e.target.value)}
                    placeholder="Enter preset name"
                  />
                  <Button
                    variant="contained"
                    onClick={handleSavePreset}
                    disabled={!presetName.trim()}
                  >
                    Save
                  </Button>
                  <Button
                    variant="outlined"
                    onClick={() => {
                      setShowPresetSave(false);
                      setPresetName('');
                    }}
                  >
                    Cancel
                  </Button>
                </Box>
              )}
            </Box>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

export default OptimizationConfigComponent;