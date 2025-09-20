/**
 * Dialog for configuring and creating new simulation jobs
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Grid,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  Chip,
  CircularProgress,
  Slider,
  FormHelperText,
} from '@mui/material';
import { ExpandMore, Warning, CheckCircle } from '@mui/icons-material';

import {
  simulationService,
  SimulationJob,
  SimulationCapabilities,
  BlastFoamConfig,
  YadeConfig,
  MeshGeometry,
  SimulationJobCreate,
} from '../../services/simulationService';

interface SimulationConfigDialogProps {
  open: boolean;
  onClose: () => void;
  onJobCreated: (job: SimulationJob) => void;
  capabilities: SimulationCapabilities | null;
}

export const SimulationConfigDialog: React.FC<SimulationConfigDialogProps> = ({
  open,
  onClose,
  onJobCreated,
  capabilities,
}) => {
  const [simulationType, setSimulationType] = useState<'physics_only' | 'blastfoam' | 'yade'>('physics_only');
  const [blastPlanId, setBlastPlanId] = useState('');
  const [priority, setPriority] = useState(5);
  const [blastfoamConfig, setBlastfoamConfig] = useState<BlastFoamConfig>(
    simulationService.createDefaultBlastFoamConfig()
  );
  const [yadeConfig, setYadeConfig] = useState<YadeConfig>(
    simulationService.createDefaultYadeConfig()
  );
  const [geometry, setGeometry] = useState<MeshGeometry>(
    simulationService.createExampleGeometry()
  );
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configErrors, setConfigErrors] = useState<string[]>([]);
  const [testingConfig, setTestingConfig] = useState(false);
  const [configTestResult, setConfigTestResult] = useState<any>(null);

  // Reset form when dialog opens
  useEffect(() => {
    if (open) {
      setSimulationType('physics_only');
      setBlastPlanId('');
      setPriority(5);
      setError(null);
      setConfigErrors([]);
      setConfigTestResult(null);
    }
  }, [open]);

  // Validate configuration when simulation type changes
  useEffect(() => {
    validateConfiguration();
  }, [simulationType, blastfoamConfig, yadeConfig]);

  const validateConfiguration = () => {
    let errors: string[] = [];
    
    if (simulationType === 'blastfoam') {
      errors = simulationService.validateBlastFoamConfig(blastfoamConfig);
    } else if (simulationType === 'yade') {
      errors = simulationService.validateYadeConfig(yadeConfig);
    }
    
    setConfigErrors(errors);
  };

  const handleTestConfiguration = async () => {
    setTestingConfig(true);
    setConfigTestResult(null);
    
    try {
      const testConfig = {
        simulation_type: simulationType,
        ...(simulationType === 'blastfoam' && { blastfoam_config: blastfoamConfig }),
        ...(simulationType === 'yade' && { yade_config: yadeConfig }),
      };
      
      const result = await simulationService.testConfig(testConfig);
      setConfigTestResult(result);
    } catch (err) {
      setError('Failed to test configuration');
      console.error('Config test error:', err);
    } finally {
      setTestingConfig(false);
    }
  };

  const handleCreateJob = async () => {
    if (configErrors.length > 0) {
      setError('Please fix configuration errors before creating job');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const jobRequest: SimulationJobCreate = {
        simulation_type: simulationType,
        geometry,
        blast_plan_id: blastPlanId || undefined,
        priority,
        ...(simulationType === 'blastfoam' && { blastfoam_config: blastfoamConfig }),
        ...(simulationType === 'yade' && { yade_config: yadeConfig }),
      };
      
      const job = await simulationService.createJob(jobRequest);
      onJobCreated(job);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create simulation job');
      console.error('Job creation error:', err);
    } finally {
      setLoading(false);
    }
  };

  const renderSimulationTypeSelector = () => (
    <FormControl fullWidth>
      <InputLabel>Simulation Type</InputLabel>
      <Select
        value={simulationType}
        label="Simulation Type"
        onChange={(e) => setSimulationType(e.target.value as any)}
      >
        <MenuItem value="physics_only">
          <Box>
            <Typography>Physics-Only</Typography>
            <Typography variant="caption" color="text.secondary">
              Fast empirical models (Kuz-Ram, PPV)
            </Typography>
          </Box>
        </MenuItem>
        
        <MenuItem 
          value="blastfoam" 
          disabled={!capabilities?.blastfoam_available}
        >
          <Box>
            <Typography>blastFoam CFD</Typography>
            <Typography variant="caption" color="text.secondary">
              High-fidelity blast wave simulation
            </Typography>
            {!capabilities?.blastfoam_available && (
              <Chip label="Not Available" size="small" color="error" />
            )}
          </Box>
        </MenuItem>
        
        <MenuItem 
          value="yade" 
          disabled={!capabilities?.yade_available}
        >
          <Box>
            <Typography>YADE DEM</Typography>
            <Typography variant="caption" color="text.secondary">
              Discrete element fragmentation modeling
            </Typography>
            {!capabilities?.yade_available && (
              <Chip label="Not Available" size="small" color="error" />
            )}
          </Box>
        </MenuItem>
      </Select>
    </FormControl>
  );

  const renderBlastFoamConfig = () => (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Typography>blastFoam Configuration</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Mesh Resolution (m)"
              type="number"
              value={blastfoamConfig.mesh_resolution}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                mesh_resolution: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0.1, max: 10, step: 0.1 }}
              helperText="Smaller values = higher resolution, longer runtime"
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Simulation Time (s)"
              type="number"
              value={blastfoamConfig.simulation_time}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                simulation_time: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0.001, max: 1, step: 0.001 }}
              helperText="Total simulation duration"
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Parallel Processes"
              type="number"
              value={blastfoamConfig.parallel_processes}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                parallel_processes: parseInt(e.target.value)
              }))}
              inputProps={{ min: 1, max: 16 }}
              helperText="Number of CPU cores to use"
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Timeout (seconds)"
              type="number"
              value={blastfoamConfig.timeout_seconds}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                timeout_seconds: parseInt(e.target.value)
              }))}
              inputProps={{ min: 60, max: 86400 }}
              helperText="Maximum simulation runtime"
            />
          </Grid>
          
          <Grid item xs={12}>
            <Typography gutterBottom>Explosive Properties</Typography>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Density (kg/m³)"
              type="number"
              value={blastfoamConfig.explosive_density}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                explosive_density: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 800, max: 2000 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Detonation Velocity (m/s)"
              type="number"
              value={blastfoamConfig.detonation_velocity}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                detonation_velocity: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 3000, max: 9000 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="CJ Pressure (Pa)"
              type="number"
              value={blastfoamConfig.chapman_jouguet_pressure}
              onChange={(e) => setBlastfoamConfig(prev => ({
                ...prev,
                chapman_jouguet_pressure: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 1e9, max: 50e9, step: 1e9 }}
            />
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );

  const renderYadeConfig = () => (
    <Accordion>
      <AccordionSummary expandIcon={<ExpandMore />}>
        <Typography>YADE Configuration</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Grid container spacing={2}>
          <Grid item xs={12}>
            <Typography gutterBottom>Particle Properties</Typography>
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Min Particle Radius (m)"
              type="number"
              value={yadeConfig.particle_radius_min}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                particle_radius_min: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0.001, max: 0.1, step: 0.001 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Max Particle Radius (m)"
              type="number"
              value={yadeConfig.particle_radius_max}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                particle_radius_max: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0.01, max: 1, step: 0.01 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Particle Density (kg/m³)"
              type="number"
              value={yadeConfig.particle_density}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                particle_density: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 1000, max: 5000 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Young's Modulus (Pa)"
              type="number"
              value={yadeConfig.young_modulus}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                young_modulus: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 1e9, max: 200e9, step: 1e9 }}
            />
          </Grid>
          
          <Grid item xs={12}>
            <Typography gutterBottom>Material Properties</Typography>
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Poisson's Ratio"
              type="number"
              value={yadeConfig.poisson_ratio}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                poisson_ratio: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0.1, max: 0.49, step: 0.01 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Friction Angle (°)"
              type="number"
              value={yadeConfig.friction_angle}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                friction_angle: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0, max: 90 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={4}>
            <TextField
              fullWidth
              label="Cohesion (Pa)"
              type="number"
              value={yadeConfig.cohesion}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                cohesion: parseFloat(e.target.value)
              }))}
              inputProps={{ min: 0, max: 50e6, step: 1e6 }}
            />
          </Grid>
          
          <Grid item xs={12}>
            <Typography gutterBottom>Simulation Parameters</Typography>
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Max Iterations"
              type="number"
              value={yadeConfig.max_iterations}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                max_iterations: parseInt(e.target.value)
              }))}
              inputProps={{ min: 1000, max: 1000000 }}
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Timeout (seconds)"
              type="number"
              value={yadeConfig.timeout_seconds}
              onChange={(e) => setYadeConfig(prev => ({
                ...prev,
                timeout_seconds: parseInt(e.target.value)
              }))}
              inputProps={{ min: 60, max: 86400 }}
            />
          </Grid>
        </Grid>
      </AccordionDetails>
    </Accordion>
  );

  const renderConfigurationTest = () => (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">Configuration Test</Typography>
          <Button
            variant="outlined"
            onClick={handleTestConfiguration}
            disabled={testingConfig || simulationType === 'physics_only'}
            startIcon={testingConfig ? <CircularProgress size={16} /> : undefined}
          >
            {testingConfig ? 'Testing...' : 'Test Configuration'}
          </Button>
        </Box>
        
        {configTestResult && (
          <Alert 
            severity={configTestResult.test_passed ? 'success' : 'error'}
            icon={configTestResult.test_passed ? <CheckCircle /> : <Warning />}
          >
            <Typography variant="subtitle2">
              {configTestResult.test_passed ? 'Configuration Valid' : 'Configuration Issues'}
            </Typography>
            {configTestResult.test_duration_seconds && (
              <Typography variant="body2">
                Test completed in {configTestResult.test_duration_seconds.toFixed(2)}s
              </Typography>
            )}
            {configTestResult.errors.length > 0 && (
              <Box mt={1}>
                {configTestResult.errors.map((error: string, index: number) => (
                  <Typography key={index} variant="body2" color="error">
                    • {error}
                  </Typography>
                ))}
              </Box>
            )}
            {configTestResult.warnings.length > 0 && (
              <Box mt={1}>
                {configTestResult.warnings.map((warning: string, index: number) => (
                  <Typography key={index} variant="body2" color="warning.main">
                    • {warning}
                  </Typography>
                ))}
              </Box>
            )}
          </Alert>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Create New Simulation</DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {configErrors.length > 0 && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="subtitle2">Configuration Errors:</Typography>
            {configErrors.map((error, index) => (
              <Typography key={index} variant="body2">• {error}</Typography>
            ))}
          </Alert>
        )}
        
        <Grid container spacing={3}>
          <Grid item xs={12}>
            {renderSimulationTypeSelector()}
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <TextField
              fullWidth
              label="Blast Plan ID (Optional)"
              value={blastPlanId}
              onChange={(e) => setBlastPlanId(e.target.value)}
              helperText="Link to existing blast plan"
            />
          </Grid>
          
          <Grid item xs={12} sm={6}>
            <Box>
              <Typography gutterBottom>Priority: {priority}</Typography>
              <Slider
                value={priority}
                onChange={(_, value) => setPriority(value as number)}
                min={0}
                max={10}
                marks
                valueLabelDisplay="auto"
              />
              <FormHelperText>Higher priority jobs run first</FormHelperText>
            </Box>
          </Grid>
          
          {simulationType === 'blastfoam' && (
            <Grid item xs={12}>
              {renderBlastFoamConfig()}
            </Grid>
          )}
          
          {simulationType === 'yade' && (
            <Grid item xs={12}>
              {renderYadeConfig()}
            </Grid>
          )}
          
          {simulationType !== 'physics_only' && (
            <Grid item xs={12}>
              {renderConfigurationTest()}
            </Grid>
          )}
        </Grid>
      </DialogContent>
      
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleCreateJob}
          disabled={loading || configErrors.length > 0}
          startIcon={loading ? <CircularProgress size={16} /> : undefined}
        >
          {loading ? 'Creating...' : 'Create Simulation'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};