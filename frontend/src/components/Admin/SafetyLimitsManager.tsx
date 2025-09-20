import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardHeader,
  TextField,
  Alert,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip
} from '@mui/material';
import {
  Save as SaveIcon,
  Refresh as RefreshIcon,
  ExpandMore as ExpandMoreIcon,
  Security as SecurityIcon,
  Warning as WarningIcon,
  LocalFireDepartment as ExplosiveIcon,
  Speed as PPVIcon
} from '@mui/icons-material';

import { adminService, SafetyLimits } from '../../services/adminService';

export const SafetyLimitsManager: React.FC = () => {
  const [safetyLimits, setSafetyLimits] = useState<SafetyLimits | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formData, setFormData] = useState<SafetyLimits | null>(null);
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    loadSafetyLimits();
  }, []);

  const loadSafetyLimits = async () => {
    try {
      setLoading(true);
      const limits = await adminService.getSafetyLimits();
      setSafetyLimits(limits);
      setFormData(limits);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load safety limits:', err);
      setError(err.message || 'Failed to load safety limits');
    } finally {
      setLoading(false);
    }
  };

  const validateForm = (): boolean => {
    if (!formData) return false;

    const errors: Record<string, string> = {};

    // Validate charge limits
    if (formData.charge_limits.max_charge_per_hole <= 0) {
      errors.max_charge_per_hole = 'Max charge per hole must be positive';
    }

    if (formData.charge_limits.max_charge_per_delay <= 0) {
      errors.max_charge_per_delay = 'Max charge per delay must be positive';
    }

    if (formData.charge_limits.max_charge_per_delay < formData.charge_limits.max_charge_per_hole) {
      errors.max_charge_per_delay = 'Max charge per delay must be >= max charge per hole';
    }

    if (formData.charge_limits.safety_factor <= 0) {
      errors.safety_factor = 'Safety factor must be positive';
    }

    // Validate powder factor limits
    if (formData.powder_factor_limits.min_powder_factor <= 0) {
      errors.min_powder_factor = 'Min powder factor must be positive';
    }

    if (formData.powder_factor_limits.max_powder_factor <= 0) {
      errors.max_powder_factor = 'Max powder factor must be positive';
    }

    if (formData.powder_factor_limits.max_powder_factor <= formData.powder_factor_limits.min_powder_factor) {
      errors.max_powder_factor = 'Max powder factor must be greater than min powder factor';
    }

    // Validate PPV limits
    if (formData.ppv_limits.default_limit <= 0) {
      errors.default_ppv_limit = 'Default PPV limit must be positive';
    }

    Object.values(formData.ppv_limits.structure_limits).forEach((limit, index) => {
      if (limit <= 0) {
        errors[`structure_limit_${index}`] = 'Structure PPV limits must be positive';
      }
    });

    // Validate distance limits
    if (formData.distance_limits.min_distance_to_structures <= 0) {
      errors.min_distance_to_structures = 'Min distance to structures must be positive';
    }

    if (formData.distance_limits.min_distance_to_roads <= 0) {
      errors.min_distance_to_roads = 'Min distance to roads must be positive';
    }

    if (formData.distance_limits.exclusion_zone_buffer <= 0) {
      errors.exclusion_zone_buffer = 'Exclusion zone buffer must be positive';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!formData || !validateForm()) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const { metadata, ...safetyData } = formData;
      await adminService.updateSafetyLimits(safetyData);
      
      setSuccess('Safety limits updated successfully. Configuration requires validation before activation.');
      await loadSafetyLimits();
    } catch (err: any) {
      console.error('Failed to update safety limits:', err);
      setError(err.message || 'Failed to update safety limits');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    if (safetyLimits) {
      setFormData(safetyLimits);
      setFormErrors({});
      setError(null);
      setSuccess(null);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography>Loading safety limits...</Typography>
      </Box>
    );
  }

  if (!formData) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography color="error">Failed to load safety limits</Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Safety Limits Configuration
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadSafetyLimits}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            onClick={handleReset}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? 'Saving...' : 'Save Changes'}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      {/* Configuration Status */}
      {safetyLimits?.metadata && (
        <Card sx={{ mb: 3 }}>
          <CardHeader 
            title="Configuration Status"
            avatar={<SecurityIcon />}
          />
          <CardContent>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">Version</Typography>
                <Typography variant="h6">{safetyLimits.metadata.version || 'N/A'}</Typography>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">Last Updated</Typography>
                <Typography variant="body2">
                  {safetyLimits.metadata.last_updated 
                    ? new Date(safetyLimits.metadata.last_updated).toLocaleDateString()
                    : 'Never'
                  }
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  By: {safetyLimits.metadata.updated_by || 'System'}
                </Typography>
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">Validation Status</Typography>
                <Chip
                  label={safetyLimits.metadata.is_validated ? 'Validated' : 'Pending Validation'}
                  color={safetyLimits.metadata.is_validated ? 'success' : 'warning'}
                  size="small"
                />
                {safetyLimits.metadata.validated_by && (
                  <Typography variant="body2" color="text.secondary">
                    By: {safetyLimits.metadata.validated_by}
                  </Typography>
                )}
              </Grid>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">Type</Typography>
                <Chip
                  label={safetyLimits.metadata.is_default ? 'Default' : 'Custom'}
                  color={safetyLimits.metadata.is_default ? 'primary' : 'secondary'}
                  size="small"
                />
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Charge Limits */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <ExplosiveIcon />
            <Typography variant="h6">Charge Limits</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Max Charge per Hole (kg)"
                type="number"
                value={formData.charge_limits.max_charge_per_hole}
                onChange={(e) => setFormData({
                  ...formData,
                  charge_limits: {
                    ...formData.charge_limits,
                    max_charge_per_hole: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.max_charge_per_hole}
                helperText={formErrors.max_charge_per_hole || 'Maximum explosive charge allowed per drill hole'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Max Charge per Delay (kg)"
                type="number"
                value={formData.charge_limits.max_charge_per_delay}
                onChange={(e) => setFormData({
                  ...formData,
                  charge_limits: {
                    ...formData.charge_limits,
                    max_charge_per_delay: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.max_charge_per_delay}
                helperText={formErrors.max_charge_per_delay || 'Maximum total charge allowed per delay timing'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Safety Factor"
                type="number"
                step="0.1"
                value={formData.charge_limits.safety_factor}
                onChange={(e) => setFormData({
                  ...formData,
                  charge_limits: {
                    ...formData.charge_limits,
                    safety_factor: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.safety_factor}
                helperText={formErrors.safety_factor || 'Additional safety margin multiplier'}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Powder Factor Limits */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <WarningIcon />
            <Typography variant="h6">Powder Factor Limits</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Min Powder Factor (kg/t)"
                type="number"
                step="0.01"
                value={formData.powder_factor_limits.min_powder_factor}
                onChange={(e) => setFormData({
                  ...formData,
                  powder_factor_limits: {
                    ...formData.powder_factor_limits,
                    min_powder_factor: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.min_powder_factor}
                helperText={formErrors.min_powder_factor || 'Minimum powder factor (kg explosive per tonne of rock)'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Max Powder Factor (kg/t)"
                type="number"
                step="0.01"
                value={formData.powder_factor_limits.max_powder_factor}
                onChange={(e) => setFormData({
                  ...formData,
                  powder_factor_limits: {
                    ...formData.powder_factor_limits,
                    max_powder_factor: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.max_powder_factor}
                helperText={formErrors.max_powder_factor || 'Maximum powder factor (kg explosive per tonne of rock)'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Recommended Range (kg/t)
                </Typography>
                <Box display="flex" gap={1} alignItems="center">
                  <TextField
                    size="small"
                    label="Min"
                    type="number"
                    step="0.01"
                    value={formData.powder_factor_limits.recommended_range[0]}
                    onChange={(e) => setFormData({
                      ...formData,
                      powder_factor_limits: {
                        ...formData.powder_factor_limits,
                        recommended_range: [
                          parseFloat(e.target.value) || 0,
                          formData.powder_factor_limits.recommended_range[1]
                        ]
                      }
                    })}
                  />
                  <Typography>-</Typography>
                  <TextField
                    size="small"
                    label="Max"
                    type="number"
                    step="0.01"
                    value={formData.powder_factor_limits.recommended_range[1]}
                    onChange={(e) => setFormData({
                      ...formData,
                      powder_factor_limits: {
                        ...formData.powder_factor_limits,
                        recommended_range: [
                          formData.powder_factor_limits.recommended_range[0],
                          parseFloat(e.target.value) || 0
                        ]
                      }
                    })}
                  />
                </Box>
              </Box>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* PPV Limits */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <PPVIcon />
            <Typography variant="h6">PPV Limits</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Default PPV Limit (mm/s)"
                type="number"
                step="0.1"
                value={formData.ppv_limits.default_limit}
                onChange={(e) => setFormData({
                  ...formData,
                  ppv_limits: {
                    ...formData.ppv_limits,
                    default_limit: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.default_ppv_limit}
                helperText={formErrors.default_ppv_limit || 'Default PPV limit for general structures'}
              />
            </Grid>
          </Grid>
          
          <Divider sx={{ my: 2 }} />
          
          <Typography variant="subtitle1" gutterBottom>
            Structure-Specific PPV Limits (mm/s)
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Residential"
                type="number"
                step="0.1"
                value={formData.ppv_limits.structure_limits.residential}
                onChange={(e) => setFormData({
                  ...formData,
                  ppv_limits: {
                    ...formData.ppv_limits,
                    structure_limits: {
                      ...formData.ppv_limits.structure_limits,
                      residential: parseFloat(e.target.value) || 0
                    }
                  }
                })}
                helperText="Residential buildings"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Commercial"
                type="number"
                step="0.1"
                value={formData.ppv_limits.structure_limits.commercial}
                onChange={(e) => setFormData({
                  ...formData,
                  ppv_limits: {
                    ...formData.ppv_limits,
                    structure_limits: {
                      ...formData.ppv_limits.structure_limits,
                      commercial: parseFloat(e.target.value) || 0
                    }
                  }
                })}
                helperText="Commercial buildings"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Industrial"
                type="number"
                step="0.1"
                value={formData.ppv_limits.structure_limits.industrial}
                onChange={(e) => setFormData({
                  ...formData,
                  ppv_limits: {
                    ...formData.ppv_limits,
                    structure_limits: {
                      ...formData.ppv_limits.structure_limits,
                      industrial: parseFloat(e.target.value) || 0
                    }
                  }
                })}
                helperText="Industrial facilities"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                label="Sensitive"
                type="number"
                step="0.1"
                value={formData.ppv_limits.structure_limits.sensitive}
                onChange={(e) => setFormData({
                  ...formData,
                  ppv_limits: {
                    ...formData.ppv_limits,
                    structure_limits: {
                      ...formData.ppv_limits.structure_limits,
                      sensitive: parseFloat(e.target.value) || 0
                    }
                  }
                })}
                helperText="Sensitive structures (hospitals, schools)"
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Distance Limits */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <SecurityIcon />
            <Typography variant="h6">Distance Limits</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Min Distance to Structures (m)"
                type="number"
                value={formData.distance_limits.min_distance_to_structures}
                onChange={(e) => setFormData({
                  ...formData,
                  distance_limits: {
                    ...formData.distance_limits,
                    min_distance_to_structures: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.min_distance_to_structures}
                helperText={formErrors.min_distance_to_structures || 'Minimum safe distance to any structure'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Min Distance to Roads (m)"
                type="number"
                value={formData.distance_limits.min_distance_to_roads}
                onChange={(e) => setFormData({
                  ...formData,
                  distance_limits: {
                    ...formData.distance_limits,
                    min_distance_to_roads: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.min_distance_to_roads}
                helperText={formErrors.min_distance_to_roads || 'Minimum safe distance to roads'}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={4}>
              <TextField
                fullWidth
                label="Exclusion Zone Buffer (m)"
                type="number"
                value={formData.distance_limits.exclusion_zone_buffer}
                onChange={(e) => setFormData({
                  ...formData,
                  distance_limits: {
                    ...formData.distance_limits,
                    exclusion_zone_buffer: parseFloat(e.target.value) || 0
                  }
                })}
                error={!!formErrors.exclusion_zone_buffer}
                helperText={formErrors.exclusion_zone_buffer || 'Additional buffer around exclusion zones'}
              />
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Regulatory Compliance */}
      {formData.regulatory_compliance && (
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">Regulatory Compliance</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={3}>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Jurisdiction"
                  value={formData.regulatory_compliance.jurisdiction}
                  onChange={(e) => setFormData({
                    ...formData,
                    regulatory_compliance: {
                      ...formData.regulatory_compliance!,
                      jurisdiction: e.target.value
                    }
                  })}
                  helperText="Regulatory jurisdiction (country, state, province)"
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Regulation Reference"
                  value={formData.regulatory_compliance.regulation_reference}
                  onChange={(e) => setFormData({
                    ...formData,
                    regulatory_compliance: {
                      ...formData.regulatory_compliance!,
                      regulation_reference: e.target.value
                    }
                  })}
                  helperText="Legal regulation reference"
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  multiline
                  rows={3}
                  label="Compliance Notes"
                  value={formData.regulatory_compliance.compliance_notes || ''}
                  onChange={(e) => setFormData({
                    ...formData,
                    regulatory_compliance: {
                      ...formData.regulatory_compliance!,
                      compliance_notes: e.target.value
                    }
                  })}
                  helperText="Additional compliance notes and requirements"
                />
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Summary Table */}
      <Card sx={{ mt: 3 }}>
        <CardHeader title="Safety Limits Summary" />
        <CardContent>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Parameter</TableCell>
                  <TableCell>Current Value</TableCell>
                  <TableCell>Unit</TableCell>
                  <TableCell>Description</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Max Charge per Hole</TableCell>
                  <TableCell>{formData.charge_limits.max_charge_per_hole}</TableCell>
                  <TableCell>kg</TableCell>
                  <TableCell>Maximum explosive charge per drill hole</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Max Charge per Delay</TableCell>
                  <TableCell>{formData.charge_limits.max_charge_per_delay}</TableCell>
                  <TableCell>kg</TableCell>
                  <TableCell>Maximum total charge per delay timing</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Default PPV Limit</TableCell>
                  <TableCell>{formData.ppv_limits.default_limit}</TableCell>
                  <TableCell>mm/s</TableCell>
                  <TableCell>Default peak particle velocity limit</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Min Distance to Structures</TableCell>
                  <TableCell>{formData.distance_limits.min_distance_to_structures}</TableCell>
                  <TableCell>m</TableCell>
                  <TableCell>Minimum safe distance to any structure</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Powder Factor Range</TableCell>
                  <TableCell>
                    {formData.powder_factor_limits.min_powder_factor} - {formData.powder_factor_limits.max_powder_factor}
                  </TableCell>
                  <TableCell>kg/t</TableCell>
                  <TableCell>Allowed powder factor range</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};