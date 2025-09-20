import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Stepper,
  Step,
  StepLabel,
  Paper,
  Alert,
  CircularProgress,
  TextField,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import {
  SiteGeometryForm,
  RockPropertiesForm,
  EquipmentSpecForm,
  ExplosivesManagement,
  ConstraintsObjectivesForm,
} from '../components/Forms';
import {
  BenchGeometry,
  RockProperties,
  DrillRigSpec,
  ExplosiveSpec,
  OptimizationConstraints,
  OptimizationObjectives,
  FormValidationState,
  Site,
} from '../types';
import apiService from '../services/api';

const steps = [
  'Site Geometry',
  'Rock Properties',
  'Equipment Specs',
  'Explosives Database',
  'Constraints & Objectives',
];

export const SiteCreate: React.FC = () => {
  const navigate = useNavigate();
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form data state
  const [siteName, setSiteName] = useState('');
  const [geometry, setGeometry] = useState<Partial<BenchGeometry>>({});
  const [rockProperties, setRockProperties] = useState<Partial<RockProperties>>({});
  const [equipmentSpec, setEquipmentSpec] = useState<Partial<DrillRigSpec>>({});
  const [explosives, setExplosives] = useState<ExplosiveSpec[]>([]);
  const [constraints, setConstraints] = useState<Partial<OptimizationConstraints>>({
    excluded_zones: [],
    sensitive_receptors: []
  });
  const [objectives, setObjectives] = useState<Partial<OptimizationObjectives>>({});

  // Validation state for each step
  const [validationStates, setValidationStates] = useState<FormValidationState[]>(
    steps.map(() => ({ isValid: false, errors: [], warnings: [] }))
  );

  const handleValidationChange = (stepIndex: number) => (validation: FormValidationState) => {
    setValidationStates(prev => {
      const newStates = [...prev];
      newStates[stepIndex] = validation;
      return newStates;
    });
  };

  const isStepValid = (stepIndex: number): boolean => {
    const validation = validationStates[stepIndex];
    
    switch (stepIndex) {
      case 0: // Site Geometry
        return validation.isValid && siteName.trim() !== '';
      case 1: // Rock Properties
        return validation.isValid;
      case 2: // Equipment Specs
        return validation.isValid;
      case 3: // Explosives
        return explosives.length > 0 && validation.isValid;
      case 4: // Constraints & Objectives
        return validation.isValid;
      default:
        return false;
    }
  };

  const handleNext = () => {
    if (activeStep < steps.length - 1) {
      setActiveStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (activeStep > 0) {
      setActiveStep(prev => prev - 1);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    try {
      // Prepare site data in the format expected by the backend
      const siteData = {
        name: siteName,
        description: `Site created with automated drill-blast system`,
        site_type: "open_pit",
        bench_geometry: geometry,
        rock_properties: {
          is_uniform: true,
          uniform_properties: rockProperties
        },
        equipment_specs: {
          drill_rigs: equipmentSpec ? [{
            name: "Default Drill Rig",
            ...equipmentSpec
          }] : [],
          explosives_catalog: explosives
        },
        operational_constraints: {
          drilling_constraints: {
            min_burden: constraints.min_burden || 2.0,
            max_burden: constraints.max_burden || 8.0,
            min_spacing: constraints.min_spacing || 2.0,
            max_spacing: constraints.max_spacing || 8.0
          },
          powder_factor_limits: {
            min_powder_factor: constraints.powder_factor_min || 0.1,
            max_powder_factor: constraints.powder_factor_max || 1.0
          },
          sensitive_receptors: constraints.sensitive_receptors || []
        }
      };

      // Submit to API
      const response = await apiService.post<Site>('/sites', siteData);
      
      if (response.success) {
        navigate('/sites');
      } else {
        setError(response.message || 'Failed to create site');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to create site');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step: number) => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Site Information
              </Typography>
              <Box sx={{ mb: 2 }}>
                <TextField
                  fullWidth
                  label="Site Name"
                  value={siteName}
                  onChange={(e) => setSiteName(e.target.value)}
                  error={siteName.trim() === ''}
                  helperText={siteName.trim() === '' ? 'Site name is required' : ''}
                  required
                />
              </Box>
            </Box>
            <SiteGeometryForm
              value={geometry}
              onChange={setGeometry}
              onValidationChange={handleValidationChange(0)}
            />
          </Box>
        );
      case 1:
        return (
          <RockPropertiesForm
            value={rockProperties}
            onChange={setRockProperties}
            onValidationChange={handleValidationChange(1)}
          />
        );
      case 2:
        return (
          <EquipmentSpecForm
            value={equipmentSpec}
            onChange={setEquipmentSpec}
            onValidationChange={handleValidationChange(2)}
          />
        );
      case 3:
        return (
          <ExplosivesManagement
            explosives={explosives}
            onChange={setExplosives}
            onValidationChange={handleValidationChange(3)}
          />
        );
      case 4:
        return (
          <ConstraintsObjectivesForm
            constraints={constraints}
            objectives={objectives}
            onConstraintsChange={setConstraints}
            onObjectivesChange={setObjectives}
            onValidationChange={handleValidationChange(4)}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Create New Site
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label, index) => (
            <Step key={label}>
              <StepLabel
                error={activeStep > index && !isStepValid(index)}
              >
                {label}
              </StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ mb: 3 }}>
          {renderStepContent(activeStep)}
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button
            onClick={handleBack}
            disabled={activeStep === 0}
          >
            Back
          </Button>

          <Box>
            {activeStep === steps.length - 1 ? (
              <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={!isStepValid(activeStep) || loading}
                startIcon={loading ? <CircularProgress size={20} /> : null}
              >
                {loading ? 'Creating...' : 'Create Site'}
              </Button>
            ) : (
              <Button
                variant="contained"
                onClick={handleNext}
                disabled={!isStepValid(activeStep)}
              >
                Next
              </Button>
            )}
          </Box>
        </Box>

        {/* Step validation summary */}
        <Box sx={{ mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            Step {activeStep + 1} of {steps.length}: {steps[activeStep]}
            {!isStepValid(activeStep) && (
              <Typography component="span" color="error" sx={{ ml: 1 }}>
                (Please complete all required fields)
              </Typography>
            )}
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};