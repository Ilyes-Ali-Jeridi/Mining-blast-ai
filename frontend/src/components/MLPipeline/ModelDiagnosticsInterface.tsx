/**
 * Model Diagnostics Interface
 * 
 * Component for viewing comprehensive model diagnostics and performance analysis.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  Divider,
} from '@mui/material';
import {
  Assessment,
  ExpandMore,
  Download,
  Refresh,
  TrendingUp,
  Warning,
  CheckCircle,
  Error,
} from '@mui/icons-material';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

import mlPipelineService from '../../services/mlPipelineService';

interface DiagnosticsData {
  model_info: any;
  feature_config: any;
  performance_history: any[];
  training_history: any[];
  retraining_recommendation: any;
  recent_performance: any;
}

const ModelDiagnosticsInterface: React.FC = () => {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadDiagnostics();
  }, []);

  const loadDiagnostics = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await mlPipelineService.exportModelDiagnostics();
      
      if (response.success) {
        setDiagnostics(response.data);
      } else {
        throw new Error(response.message || 'Failed to load diagnostics');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load diagnostics');
    } finally {
      setLoading(false);
    }
  };

  const handleExportDiagnostics = async () => {
    if (!diagnostics) return;

    setExporting(true);
    try {
      const dataStr = JSON.stringify(diagnostics, null, 2);
      const dataBlob = new Blob([dataStr], { type: 'application/json' });
      const url = URL.createObjectURL(dataBlob);
      
      const link = document.createElement('a');
      link.href = url;
      link.download = `model_diagnostics_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export diagnostics');
    } finally {
      setExporting(false);
    }
  };

  const getStatusIcon = (status: boolean) => {
    return status ? <CheckCircle color="success" /> : <Error color="error" />;
  };

  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      default: return 'success';
    }
  };

  const formatFeatureImportance = (importance: Record<string, number>) => {
    return Object.entries(importance)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([feature, value]) => ({
        feature: feature.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        importance: value,
      }));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={loadDiagnostics}>
          Retry
        </Button>
      }>
        {error}
      </Alert>
    );
  }

  if (!diagnostics) {
    return (
      <Alert severity="info">
        No diagnostics data available. Train a model to see diagnostics.
      </Alert>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5">
          Model Diagnostics
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            onClick={loadDiagnostics}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <Refresh />}
          >
            Refresh
          </Button>
          
          <Button
            variant="contained"
            onClick={handleExportDiagnostics}
            disabled={exporting}
            startIcon={exporting ? <CircularProgress size={16} /> : <Download />}
          >
            Export
          </Button>
        </Box>
      </Box>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Comprehensive analysis of model performance, feature importance, and recommendations
        for improving prediction accuracy.
      </Typography>

      <Grid container spacing={3}>
        {/* Model Overview */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
                Model Overview
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    {getStatusIcon(diagnostics.model_info.is_trained)}
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Training Status
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {diagnostics.model_info.is_trained ? 'Trained' : 'Not Trained'}
                    </Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6">
                      {diagnostics.model_info.validation_r2?.toFixed(3) || 'N/A'}
                    </Typography>
                    <Typography variant="body2">
                      Validation R²
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Model Accuracy
                    </Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Typography variant="h6">
                      {diagnostics.model_info.training_samples || 0}
                    </Typography>
                    <Typography variant="body2">
                      Training Samples
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Data Points Used
                    </Typography>
                  </Box>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Box sx={{ textAlign: 'center' }}>
                    <Chip
                      label={diagnostics.model_info.is_reliable ? 'Reliable' : 'Unreliable'}
                      color={diagnostics.model_info.is_reliable ? 'success' : 'error'}
                      size="small"
                    />
                    <Typography variant="body2" sx={{ mt: 1 }}>
                      Reliability
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Model Quality
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Retraining Recommendation */}
        {diagnostics.retraining_recommendation && (
          <Grid item xs={12}>
            <Alert
              severity={diagnostics.retraining_recommendation.should_retrain 
                ? getUrgencyColor(diagnostics.retraining_recommendation.urgency) 
                : 'success'}
            >
              <Typography variant="body2" sx={{ fontWeight: 'bold' }}>
                {diagnostics.retraining_recommendation.should_retrain 
                  ? `Retraining Recommended (${diagnostics.retraining_recommendation.urgency} priority)`
                  : 'Model is Up to Date'}
              </Typography>
              <Typography variant="body2">
                {diagnostics.retraining_recommendation.recommended_action}
              </Typography>
              {diagnostics.retraining_recommendation.reasons?.length > 0 && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Reasons: {diagnostics.retraining_recommendation.reasons.join(', ')}
                </Typography>
              )}
            </Alert>
          </Grid>
        )}

        {/* Feature Importance */}
        {diagnostics.training_history?.length > 0 && 
         diagnostics.training_history[diagnostics.training_history.length - 1]?.feature_importance && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Feature Importance
                </Typography>

                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={formatFeatureImportance(
                      diagnostics.training_history[diagnostics.training_history.length - 1].feature_importance
                    )}
                    layout="horizontal"
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="feature" type="category" width={100} />
                    <Tooltip />
                    <Bar dataKey="importance" fill="#1976d2" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Performance History */}
        {diagnostics.performance_history?.length > 0 && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Performance History
                </Typography>

                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={diagnostics.performance_history}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis domain={[0, 1]} />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                      formatter={(value: number) => [value.toFixed(3), 'R²']}
                    />
                    <Line
                      type="monotone"
                      dataKey="validation_r2"
                      stroke="#1976d2"
                      strokeWidth={2}
                      dot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Recent Performance */}
        {diagnostics.recent_performance && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Recent Performance
                </Typography>

                <TableContainer>
                  <Table size="small">
                    <TableBody>
                      <TableRow>
                        <TableCell>Sample Count</TableCell>
                        <TableCell align="right">
                          {diagnostics.recent_performance.sample_count || 0}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>R² Score</TableCell>
                        <TableCell align="right">
                          {diagnostics.recent_performance.r2_score?.toFixed(3) || 'N/A'}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>RMSE</TableCell>
                        <TableCell align="right">
                          {diagnostics.recent_performance.rmse?.toFixed(2) || 'N/A'}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>MAE</TableCell>
                        <TableCell align="right">
                          {diagnostics.recent_performance.mae?.toFixed(2) || 'N/A'}
                        </TableCell>
                      </TableRow>
                      <TableRow>
                        <TableCell>Prediction Bias</TableCell>
                        <TableCell align="right">
                          {diagnostics.recent_performance.prediction_bias?.toFixed(2) || 'N/A'}
                        </TableCell>
                      </TableRow>
                    </TableBody>
                  </Table>
                </TableContainer>

                {diagnostics.recent_performance.time_range && (
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                    Time Range: {new Date(diagnostics.recent_performance.time_range.start).toLocaleDateString()} - {new Date(diagnostics.recent_performance.time_range.end).toLocaleDateString()}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Feature Configuration */}
        {diagnostics.feature_config && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Feature Engineering Configuration
                </Typography>

                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Interaction Terms"
                      secondary={diagnostics.feature_config.include_interaction_terms ? 'Enabled' : 'Disabled'}
                    />
                    {getStatusIcon(diagnostics.feature_config.include_interaction_terms)}
                  </ListItem>
                  
                  <ListItem>
                    <ListItemText
                      primary="Polynomial Features"
                      secondary={diagnostics.feature_config.include_polynomial_features ? 'Enabled' : 'Disabled'}
                    />
                    {getStatusIcon(diagnostics.feature_config.include_polynomial_features)}
                  </ListItem>
                  
                  <ListItem>
                    <ListItemText
                      primary="Feature Normalization"
                      secondary={diagnostics.feature_config.normalize_features ? 'Enabled' : 'Disabled'}
                    />
                    {getStatusIcon(diagnostics.feature_config.normalize_features)}
                  </ListItem>
                  
                  <ListItem>
                    <ListItemText
                      primary="Polynomial Degree"
                      secondary={diagnostics.feature_config.polynomial_degree || 'N/A'}
                    />
                  </ListItem>
                  
                  <ListItem>
                    <ListItemText
                      primary="Feature Selection Threshold"
                      secondary={diagnostics.feature_config.feature_selection_threshold || 'N/A'}
                    />
                  </ListItem>
                </List>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Training History Details */}
        {diagnostics.training_history?.length > 0 && (
          <Grid item xs={12}>
            <Accordion>
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Typography variant="h6">Training History Details</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Version</TableCell>
                        <TableCell>Date</TableCell>
                        <TableCell align="right">Samples</TableCell>
                        <TableCell align="right">Train R²</TableCell>
                        <TableCell align="right">Val R²</TableCell>
                        <TableCell align="right">CV R²</TableCell>
                        <TableCell>Reliable</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {diagnostics.training_history.map((history, index) => (
                        <TableRow key={index}>
                          <TableCell>{history.model_version}</TableCell>
                          <TableCell>
                            {new Date(history.training_timestamp).toLocaleDateString()}
                          </TableCell>
                          <TableCell align="right">{history.training_samples}</TableCell>
                          <TableCell align="right">{history.train_r2?.toFixed(3)}</TableCell>
                          <TableCell align="right">{history.val_r2?.toFixed(3)}</TableCell>
                          <TableCell align="right">{history.cv_r2_mean?.toFixed(3)}</TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={history.is_reliable ? 'Yes' : 'No'}
                              color={history.is_reliable ? 'success' : 'error'}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </AccordionDetails>
            </Accordion>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ModelDiagnosticsInterface;