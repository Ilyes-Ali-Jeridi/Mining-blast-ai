import React, { useState } from 'react';
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
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  Save as SaveIcon,
  Science as ScienceIcon,
  ExpandMore as ExpandMoreIcon,
  TrendingUp as TrendingUpIcon,
  Speed as PPVIcon,
  Grain as FragmentIcon
} from '@mui/icons-material';

import { adminService } from '../../services/adminService';

interface CalibrationData {
  rock_factor_a?: number;
  ppv_constants?: {
    k?: number;
    a?: number;
    b?: number;
  };
  notes?: string;
}

export const PhysicsCalibration: React.FC = () => {
  const [calibrationData, setCalibrationData] = useState<CalibrationData>({
    rock_factor_a: 7.0,
    ppv_constants: {
      k: 1.4,
      a: 0.333,
      b: 1.6
    },
    notes: ''
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);

  const handleCalibrate = async () => {
    if (!validateCalibrationData()) {
      return;
    }

    setSubmitting(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await adminService.calibratePhysicsParameters(calibrationData);
      setSuccess(`Physics parameters calibrated successfully. New configuration version: ${result.version}`);
      setConfirmDialogOpen(false);
    } catch (err: any) {
      console.error('Failed to calibrate physics parameters:', err);
      setError(err.message || 'Failed to calibrate physics parameters');
    } finally {
      setSubmitting(false);
    }
  };

  const validateCalibrationData = (): boolean => {
    if (calibrationData.rock_factor_a && calibrationData.rock_factor_a <= 0) {
      setError('Rock Factor A must be positive');
      return false;
    }

    if (calibrationData.ppv_constants) {
      const { k, a, b } = calibrationData.ppv_constants;
      if (k && k <= 0) {
        setError('PPV constant K must be positive');
        return false;
      }
      if (a && a <= 0) {
        setError('PPV constant A must be positive');
        return false;
      }
      if (b && b <= 0) {
        setError('PPV constant B must be positive');
        return false;
      }
    }

    return true;
  };

  const handleConfirmCalibration = () => {
    if (validateCalibrationData()) {
      setConfirmDialogOpen(true);
    }
  };

  const resetToDefaults = () => {
    setCalibrationData({
      rock_factor_a: 7.0,
      ppv_constants: {
        k: 1.4,
        a: 0.333,
        b: 1.6
      },
      notes: ''
    });
    setError(null);
    setSuccess(null);
  };

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Physics Model Calibration
        </Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            onClick={resetToDefaults}
          >
            Reset to Defaults
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleConfirmCalibration}
            disabled={submitting}
          >
            {submitting ? 'Calibrating...' : 'Calibrate Parameters'}
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      {/* Calibration Warning */}
      <Alert severity="warning" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Warning:</strong> Calibrating physics parameters will create a new configuration version 
          and affect all future blast plan calculations. Ensure you have validated measurement data 
          before proceeding with calibration.
        </Typography>
      </Alert>

      {/* Kuz-Ram Parameters */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <FragmentIcon />
            <Typography variant="h6">Kuz-Ram Fragmentation Model</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Rock Factor A Calibration" />
                <CardContent>
                  <TextField
                    fullWidth
                    label="Rock Factor A"
                    type="number"
                    step="0.1"
                    value={calibrationData.rock_factor_a || ''}
                    onChange={(e) => setCalibrationData({
                      ...calibrationData,
                      rock_factor_a: parseFloat(e.target.value) || undefined
                    })}
                    helperText="Typical range: 5.0 - 10.0. Default: 7.0"
                    sx={{ mb: 2 }}
                  />
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    The Rock Factor A parameter controls the mean fragment size in the Kuz-Ram equation:
                  </Typography>
                  <Typography variant="body2" sx={{ fontFamily: 'monospace', mb: 2 }}>
                    X₅₀ = A × (V/Q)^0.8 × Q^0.167 × (115/E)^0.633
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
                    <strong>Calibration Guidelines:</strong>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Lower values (5-6): Harder, more competent rock
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Higher values (8-10): Softer, more fractured rock
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card>
                <CardHeader title="Calibration Impact" />
                <CardContent>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Current Rock Factor A: <strong>{calibrationData.rock_factor_a || 'Not set'}</strong>
                  </Typography>
                  
                  <Divider sx={{ my: 2 }} />
                  
                  <Typography variant="subtitle2" gutterBottom>
                    Expected Fragment Size Changes:
                  </Typography>
                  
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Rock Factor A</TableCell>
                        <TableCell>Relative P50</TableCell>
                        <TableCell>Rock Type</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      <TableRow>
                        <TableCell>5.0</TableCell>
                        <TableCell>-29%</TableCell>
                        <TableCell>Very hard</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>7.0</TableCell>
                        <TableCell>0% (baseline)</TableCell>
                        <TableCell>Medium</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>9.0</TableCell>
                        <TableCell>+29%</TableCell>
                        <TableCell>Soft/fractured</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* PPV Parameters */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <PPVIcon />
            <Typography variant="h6">PPV Prediction Model</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <Card>
                <CardHeader title="PPV Constants Calibration" />
                <CardContent>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    PPV Equation: PPV = K × (W^A / R^B)
                  </Typography>
                  
                  <Grid container spacing={2} sx={{ mt: 1 }}>
                    <Grid item xs={12} sm={4}>
                      <TextField
                        fullWidth
                        label="K Constant"
                        type="number"
                        step="0.1"
                        value={calibrationData.ppv_constants?.k || ''}
                        onChange={(e) => setCalibrationData({
                          ...calibrationData,
                          ppv_constants: {
                            ...calibrationData.ppv_constants,
                            k: parseFloat(e.target.value) || undefined
                          }
                        })}
                        helperText="Site factor (0.5 - 3.0)"
                      />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <TextField
                        fullWidth
                        label="A Exponent"
                        type="number"
                        step="0.01"
                        value={calibrationData.ppv_constants?.a || ''}
                        onChange={(e) => setCalibrationData({
                          ...calibrationData,
                          ppv_constants: {
                            ...calibrationData.ppv_constants,
                            a: parseFloat(e.target.value) || undefined
                          }
                        })}
                        helperText="Charge exponent (0.2 - 0.5)"
                      />
                    </Grid>
                    <Grid item xs={12} sm={4}>
                      <TextField
                        fullWidth
                        label="B Exponent"
                        type="number"
                        step="0.01"
                        value={calibrationData.ppv_constants?.b || ''}
                        onChange={(e) => setCalibrationData({
                          ...calibrationData,
                          ppv_constants: {
                            ...calibrationData.ppv_constants,
                            b: parseFloat(e.target.value) || undefined
                          }
                        })}
                        helperText="Distance exponent (1.0 - 2.0)"
                      />
                    </Grid>
                  </Grid>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    <strong>Parameter Guidelines:</strong>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • K: Site-specific factor affected by geology and blast design
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • A: Charge weight scaling (typically 0.33 for spherical charges)
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • B: Distance attenuation (typically 1.6 for most sites)
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card>
                <CardHeader title="Typical Values" />
                <CardContent>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Parameter</TableCell>
                        <TableCell>Typical Range</TableCell>
                        <TableCell>Default</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      <TableRow>
                        <TableCell>K</TableCell>
                        <TableCell>0.5 - 3.0</TableCell>
                        <TableCell>1.4</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>A</TableCell>
                        <TableCell>0.2 - 0.5</TableCell>
                        <TableCell>0.333</TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>B</TableCell>
                        <TableCell>1.0 - 2.0</TableCell>
                        <TableCell>1.6</TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                  
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    <strong>Rock Type Factors:</strong>
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Hard rock: K = 0.8-1.2
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Medium rock: K = 1.2-1.8
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    • Soft rock: K = 1.8-2.5
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </AccordionDetails>
      </Accordion>

      {/* Calibration Notes */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Box display="flex" alignItems="center" gap={1}>
            <ScienceIcon />
            <Typography variant="h6">Calibration Notes</Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <TextField
            fullWidth
            multiline
            rows={6}
            label="Calibration Notes"
            value={calibrationData.notes || ''}
            onChange={(e) => setCalibrationData({
              ...calibrationData,
              notes: e.target.value
            })}
            placeholder="Document the calibration process, measurement data used, validation results, and any site-specific considerations..."
            helperText="These notes will be stored with the calibrated configuration for audit purposes"
          />
          
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            <strong>Recommended calibration documentation:</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Source of measurement data (number of blasts, date range)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Validation metrics (R², RMSE, bias)
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Site conditions and rock properties
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Blast design parameters used in calibration
          </Typography>
          <Typography variant="body2" color="text.secondary">
            • Expected improvement in prediction accuracy
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* Current vs Calibrated Summary */}
      <Card sx={{ mt: 3 }}>
        <CardHeader title="Calibration Summary" />
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Parameter</TableCell>
                  <TableCell>Current Default</TableCell>
                  <TableCell>Calibrated Value</TableCell>
                  <TableCell>Change</TableCell>
                  <TableCell>Impact</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell>Rock Factor A</TableCell>
                  <TableCell>7.0</TableCell>
                  <TableCell>{calibrationData.rock_factor_a || 'Not set'}</TableCell>
                  <TableCell>
                    {calibrationData.rock_factor_a ? 
                      `${((calibrationData.rock_factor_a - 7.0) / 7.0 * 100).toFixed(1)}%` : 
                      'N/A'
                    }
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={
                        !calibrationData.rock_factor_a ? 'No change' :
                        calibrationData.rock_factor_a > 7.0 ? 'Larger fragments' : 'Smaller fragments'
                      }
                      color={
                        !calibrationData.rock_factor_a ? 'default' :
                        calibrationData.rock_factor_a > 7.0 ? 'warning' : 'success'
                      }
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>PPV K Constant</TableCell>
                  <TableCell>1.4</TableCell>
                  <TableCell>{calibrationData.ppv_constants?.k || 'Not set'}</TableCell>
                  <TableCell>
                    {calibrationData.ppv_constants?.k ? 
                      `${((calibrationData.ppv_constants.k - 1.4) / 1.4 * 100).toFixed(1)}%` : 
                      'N/A'
                    }
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={
                        !calibrationData.ppv_constants?.k ? 'No change' :
                        calibrationData.ppv_constants.k > 1.4 ? 'Higher PPV' : 'Lower PPV'
                      }
                      color={
                        !calibrationData.ppv_constants?.k ? 'default' :
                        calibrationData.ppv_constants.k > 1.4 ? 'error' : 'success'
                      }
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>PPV A Exponent</TableCell>
                  <TableCell>0.333</TableCell>
                  <TableCell>{calibrationData.ppv_constants?.a || 'Not set'}</TableCell>
                  <TableCell>
                    {calibrationData.ppv_constants?.a ? 
                      `${((calibrationData.ppv_constants.a - 0.333) / 0.333 * 100).toFixed(1)}%` : 
                      'N/A'
                    }
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={
                        !calibrationData.ppv_constants?.a ? 'No change' :
                        Math.abs(calibrationData.ppv_constants.a - 0.333) < 0.01 ? 'Minimal change' : 'Charge scaling'
                      }
                      color="primary"
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>PPV B Exponent</TableCell>
                  <TableCell>1.6</TableCell>
                  <TableCell>{calibrationData.ppv_constants?.b || 'Not set'}</TableCell>
                  <TableCell>
                    {calibrationData.ppv_constants?.b ? 
                      `${((calibrationData.ppv_constants.b - 1.6) / 1.6 * 100).toFixed(1)}%` : 
                      'N/A'
                    }
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={
                        !calibrationData.ppv_constants?.b ? 'No change' :
                        Math.abs(calibrationData.ppv_constants.b - 1.6) < 0.1 ? 'Minimal change' : 'Distance scaling'
                      }
                      color="primary"
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Confirmation Dialog */}
      <Dialog 
        open={confirmDialogOpen} 
        onClose={() => setConfirmDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Confirm Physics Parameter Calibration
        </DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            This action will create a new physics configuration version and affect all future blast calculations.
          </Alert>
          
          <Typography variant="body2" gutterBottom>
            <strong>Parameters to be calibrated:</strong>
          </Typography>
          
          {calibrationData.rock_factor_a && (
            <Typography variant="body2">
              • Rock Factor A: {calibrationData.rock_factor_a}
            </Typography>
          )}
          
          {calibrationData.ppv_constants?.k && (
            <Typography variant="body2">
              • PPV K Constant: {calibrationData.ppv_constants.k}
            </Typography>
          )}
          
          {calibrationData.ppv_constants?.a && (
            <Typography variant="body2">
              • PPV A Exponent: {calibrationData.ppv_constants.a}
            </Typography>
          )}
          
          {calibrationData.ppv_constants?.b && (
            <Typography variant="body2">
              • PPV B Exponent: {calibrationData.ppv_constants.b}
            </Typography>
          )}
          
          {calibrationData.notes && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" gutterBottom>
                <strong>Calibration Notes:</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {calibrationData.notes}
              </Typography>
            </Box>
          )}
          
          <Typography variant="body2" sx={{ mt: 2 }}>
            Are you sure you want to proceed with this calibration?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleCalibrate}
            variant="contained"
            disabled={submitting}
            color="warning"
          >
            {submitting ? 'Calibrating...' : 'Confirm Calibration'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};