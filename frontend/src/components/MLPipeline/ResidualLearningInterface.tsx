/**
 * Residual Learning Interface
 * 
 * Component for training and using residual learning models to improve physics predictions.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Alert,
  CircularProgress,
  Chip,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import {
  ModelTraining,
  Psychology,
  TrendingUp,
  ExpandMore,
  CheckCircle,
  Warning,
  Error,
  Refresh,
} from '@mui/icons-material';

import mlPipelineService, {
  BlastParameters,
  ModelStatus,
  RetrainingRecommendation,
  ResidualLearningPrediction,
} from '../../services/mlPipelineService';

interface TrainingState {
  loading: boolean;
  progress: number;
  error: string | null;
  result: any | null;
}

interface PredictionState {
  loading: boolean;
  result: ResidualLearningPrediction | null;
  error: string | null;
}

const ResidualLearningInterface: React.FC = () => {
  const [modelStatus, setModelStatus] = useState<ModelStatus | null>(null);
  const [retrainingRec, setRetrainingRec] = useState<RetrainingRecommendation | null>(null);
  const [statusLoading, setStatusLoading] = useState(true);
  
  const [trainingState, setTrainingState] = useState<TrainingState>({
    loading: false,
    progress: 0,
    error: null,
    result: null,
  });

  const [predictionState, setPredictionState] = useState<PredictionState>({
    loading: false,
    result: null,
    error: null,
  });

  const [blastParams, setBlastParams] = useState<BlastParameters>({
    burden_m: 3.0,
    spacing_m: 3.5,
    bench_height_m: 12.0,
    hole_diameter_mm: 165.0,
    stemming_length_m: 3.0,
    powder_factor_kg_per_t: 0.5,
    powder_factor_kg_per_m3: 1.35,
    rock_density_kg_m3: 2700.0,
    explosive_rws: 100.0,
    explosive_density_kg_m3: 1200.0,
  });

  const [predictionType, setPredictionType] = useState<string>('fragmentation');
  const [selectedBlastRecords, setSelectedBlastRecords] = useState<string>('');

  useEffect(() => {
    loadModelStatus();
  }, []);

  const loadModelStatus = async () => {
    try {
      setStatusLoading(true);
      const response = await mlPipelineService.getResidualLearningStatus();
      
      if (response.success) {
        setModelStatus(response.data.model_status);
        setRetrainingRec(response.data.retraining_recommendation);
      }
    } catch (error) {
      console.error('Failed to load model status:', error);
    } finally {
      setStatusLoading(false);
    }
  };

  const handleTrainModel = async () => {
    if (!selectedBlastRecords.trim()) {
      setTrainingState(prev => ({ ...prev, error: 'Please enter blast record IDs' }));
      return;
    }

    const blastRecordIds = selectedBlastRecords
      .split(',')
      .map(id => parseInt(id.trim()))
      .filter(id => !isNaN(id));

    if (blastRecordIds.length === 0) {
      setTrainingState(prev => ({ ...prev, error: 'Please enter valid blast record IDs' }));
      return;
    }

    setTrainingState({
      loading: true,
      progress: 0,
      error: null,
      result: null,
    });

    try {
      // Simulate training progress
      const progressInterval = setInterval(() => {
        setTrainingState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90),
        }));
      }, 500);

      const response = await mlPipelineService.trainResidualModel(blastRecordIds, 0.2, 5);

      clearInterval(progressInterval);

      if (response.success) {
        setTrainingState({
          loading: false,
          progress: 100,
          error: null,
          result: response.data,
        });
        
        // Reload model status
        await loadModelStatus();
      } else {
        throw new Error(response.message || 'Training failed');
      }
    } catch (error) {
      setTrainingState({
        loading: false,
        progress: 0,
        error: error instanceof Error ? error.message : 'Training failed',
        result: null,
      });
    }
  };

  const handlePredict = async () => {
    setPredictionState({ loading: true, result: null, error: null });

    try {
      const response = await mlPipelineService.predictWithCorrection(blastParams, predictionType);

      if (response.success) {
        setPredictionState({
          loading: false,
          result: response.data.prediction_result,
          error: null,
        });
      } else {
        throw new Error(response.message || 'Prediction failed');
      }
    } catch (error) {
      setPredictionState({
        loading: false,
        result: null,
        error: error instanceof Error ? error.message : 'Prediction failed',
      });
    }
  };

  const handleParamChange = (field: keyof BlastParameters, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setBlastParams(prev => ({ ...prev, [field]: numValue }));
    }
  };

  const getStatusColor = (status: boolean) => status ? 'success' : 'error';
  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      default: return 'success';
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Residual Learning
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Train XGBoost models to learn corrections to physics-based predictions using post-blast measurement data.
        The residual model enhances physics predictions while keeping them as the primary source.
      </Typography>

      <Grid container spacing={3}>
        {/* Model Status */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">
                  <Psychology sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Model Status
                </Typography>
                <Button
                  size="small"
                  onClick={loadModelStatus}
                  disabled={statusLoading}
                  startIcon={statusLoading ? <CircularProgress size={16} /> : <Refresh />}
                >
                  Refresh
                </Button>
              </Box>

              {statusLoading ? (
                <CircularProgress />
              ) : modelStatus ? (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Chip
                        label={modelStatus.is_trained ? 'Trained' : 'Not Trained'}
                        color={getStatusColor(modelStatus.is_trained)}
                        sx={{ mb: 1 }}
                      />
                      <Typography variant="body2" color="text.secondary">
                        Training Status
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">
                        {modelStatus.validation_r2.toFixed(3)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Validation R²
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">
                        {modelStatus.training_samples}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Training Samples
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={3}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Chip
                        label={modelStatus.is_reliable ? 'Reliable' : 'Unreliable'}
                        color={getStatusColor(modelStatus.is_reliable)}
                        sx={{ mb: 1 }}
                      />
                      <Typography variant="body2" color="text.secondary">
                        Reliability
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
              ) : (
                <Alert severity="warning">Failed to load model status</Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Retraining Recommendation */}
        {retrainingRec && (
          <Grid item xs={12}>
            <Alert
              severity={retrainingRec.should_retrain ? getUrgencyColor(retrainingRec.urgency) : 'success'}
              action={
                retrainingRec.should_retrain && (
                  <Button color="inherit" size="small">
                    Train Now
                  </Button>
                )
              }
            >
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                {retrainingRec.should_retrain ? 'Retraining Recommended' : 'Model Up to Date'}
              </Typography>
              <Typography variant="body2">
                {retrainingRec.recommended_action}
              </Typography>
              {retrainingRec.reasons.length > 0 && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Reasons: {retrainingRec.reasons.join(', ')}
                </Typography>
              )}
            </Alert>
          </Grid>
        )}

        {/* Model Training */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <ModelTraining sx={{ mr: 1, verticalAlign: 'middle' }} />
                Train Model
              </Typography>

              <TextField
                fullWidth
                label="Blast Record IDs"
                value={selectedBlastRecords}
                onChange={(e) => setSelectedBlastRecords(e.target.value)}
                placeholder="1, 2, 3, 4, 5"
                helperText="Enter comma-separated blast record IDs for training"
                sx={{ mb: 2 }}
                disabled={trainingState.loading}
              />

              <Button
                fullWidth
                variant="contained"
                onClick={handleTrainModel}
                disabled={trainingState.loading || !selectedBlastRecords.trim()}
                startIcon={trainingState.loading ? <CircularProgress size={20} /> : <ModelTraining />}
                sx={{ mb: 2 }}
              >
                {trainingState.loading ? 'Training...' : 'Train Residual Model'}
              </Button>

              {trainingState.loading && (
                <Box sx={{ mb: 2 }}>
                  <LinearProgress variant="determinate" value={trainingState.progress} />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Training progress: {trainingState.progress}%
                  </Typography>
                </Box>
              )}

              {trainingState.error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {trainingState.error}
                </Alert>
              )}

              {trainingState.result && (
                <Alert severity="success">
                  <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                    Training Completed Successfully
                  </Typography>
                  <Typography variant="body2">
                    Validation R²: {trainingState.result.model_metrics?.validation_r2?.toFixed(3) || 'N/A'}
                  </Typography>
                  <Typography variant="body2">
                    Training Samples: {trainingState.result.model_metrics?.training_samples || 'N/A'}
                  </Typography>
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Prediction Interface */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
                Make Prediction
              </Typography>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel>Prediction Type</InputLabel>
                <Select
                  value={predictionType}
                  onChange={(e) => setPredictionType(e.target.value)}
                  label="Prediction Type"
                >
                  <MenuItem value="fragmentation">Fragmentation</MenuItem>
                  <MenuItem value="ppv">PPV</MenuItem>
                </Select>
              </FormControl>

              <Button
                fullWidth
                variant="contained"
                onClick={handlePredict}
                disabled={predictionState.loading || !modelStatus?.is_trained}
                startIcon={predictionState.loading ? <CircularProgress size={20} /> : <TrendingUp />}
                sx={{ mb: 2 }}
              >
                {predictionState.loading ? 'Predicting...' : 'Predict with Correction'}
              </Button>

              {!modelStatus?.is_trained && (
                <Alert severity="warning" sx={{ mb: 2 }}>
                  Model must be trained before making predictions
                </Alert>
              )}

              {predictionState.error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {predictionState.error}
                </Alert>
              )}

              {predictionState.result && (
                <Paper sx={{ p: 2, backgroundColor: 'background.default' }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 1 }}>
                    Prediction Results:
                  </Typography>
                  
                  <Grid container spacing={1}>
                    <Grid item xs={6}>
                      <Typography variant="body2">Physics:</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        {predictionState.result.physics_prediction.toFixed(2)} mm
                      </Typography>
                    </Grid>
                    
                    <Grid item xs={6}>
                      <Typography variant="body2">ML Correction:</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        {predictionState.result.ml_correction >= 0 ? '+' : ''}
                        {predictionState.result.ml_correction.toFixed(2)} mm
                      </Typography>
                    </Grid>
                    
                    <Grid item xs={6}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>Final:</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                        {predictionState.result.corrected_prediction.toFixed(2)} mm
                      </Typography>
                    </Grid>
                    
                    <Grid item xs={6}>
                      <Typography variant="body2">Confidence:</Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="body2">
                        {(predictionState.result.confidence * 100).toFixed(1)}%
                      </Typography>
                    </Grid>
                  </Grid>
                </Paper>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Blast Parameters */}
        <Grid item xs={12}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMore />}>
              <Typography variant="h6">Blast Parameters</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Burden (m)"
                    type="number"
                    value={blastParams.burden_m}
                    onChange={(e) => handleParamChange('burden_m', e.target.value)}
                    inputProps={{ step: 0.1, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Spacing (m)"
                    type="number"
                    value={blastParams.spacing_m}
                    onChange={(e) => handleParamChange('spacing_m', e.target.value)}
                    inputProps={{ step: 0.1, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Bench Height (m)"
                    type="number"
                    value={blastParams.bench_height_m}
                    onChange={(e) => handleParamChange('bench_height_m', e.target.value)}
                    inputProps={{ step: 0.1, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Hole Diameter (mm)"
                    type="number"
                    value={blastParams.hole_diameter_mm}
                    onChange={(e) => handleParamChange('hole_diameter_mm', e.target.value)}
                    inputProps={{ step: 1, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Stemming Length (m)"
                    type="number"
                    value={blastParams.stemming_length_m}
                    onChange={(e) => handleParamChange('stemming_length_m', e.target.value)}
                    inputProps={{ step: 0.1, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Powder Factor (kg/t)"
                    type="number"
                    value={blastParams.powder_factor_kg_per_t}
                    onChange={(e) => handleParamChange('powder_factor_kg_per_t', e.target.value)}
                    inputProps={{ step: 0.01, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Rock Density (kg/m³)"
                    type="number"
                    value={blastParams.rock_density_kg_m3}
                    onChange={(e) => handleParamChange('rock_density_kg_m3', e.target.value)}
                    inputProps={{ step: 10, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Explosive RWS (%)"
                    type="number"
                    value={blastParams.explosive_rws}
                    onChange={(e) => handleParamChange('explosive_rws', e.target.value)}
                    inputProps={{ step: 1, min: 0 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6} md={4}>
                  <TextField
                    fullWidth
                    label="Explosive Density (kg/m³)"
                    type="number"
                    value={blastParams.explosive_density_kg_m3}
                    onChange={(e) => handleParamChange('explosive_density_kg_m3', e.target.value)}
                    inputProps={{ step: 10, min: 0 }}
                  />
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Grid>
      </Grid>
    </Box>
  );
};

export default ResidualLearningInterface;