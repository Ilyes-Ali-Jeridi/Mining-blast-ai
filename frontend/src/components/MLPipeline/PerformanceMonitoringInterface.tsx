/**
 * Performance Monitoring Interface
 * 
 * Component for monitoring ML model performance and detecting drift.
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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Timeline,
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Refresh,
  Add,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
} from 'recharts';

import mlPipelineService, { PerformanceMetrics } from '../../services/mlPipelineService';

interface MonitoringData {
  predicted: number;
  actual: number;
  timestamp: string;
  error: number;
  relativeError: number;
}

const PerformanceMonitoringInterface: React.FC = () => {
  const [performanceHistory, setPerformanceHistory] = useState<PerformanceMetrics[]>([]);
  const [monitoringData, setMonitoringData] = useState<MonitoringData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [newPrediction, setNewPrediction] = useState({
    predicted: '',
    actual: '',
    timestamp: new Date().toISOString().slice(0, 16), // YYYY-MM-DDTHH:MM format
  });
  
  const [submitting, setSubmitting] = useState(false);
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    loadPerformanceData();
  }, []);

  const loadPerformanceData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await mlPipelineService.getResidualLearningStatus();
      
      if (response.success) {
        setPerformanceHistory(response.data.performance_history || []);
        
        // Generate some mock monitoring data for demonstration
        const mockData: MonitoringData[] = [];
        for (let i = 0; i < 20; i++) {
          const predicted = 50 + Math.random() * 30;
          const actual = predicted + (Math.random() - 0.5) * 10;
          const timestamp = new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString();
          
          mockData.push({
            predicted,
            actual,
            timestamp,
            error: Math.abs(predicted - actual),
            relativeError: Math.abs(predicted - actual) / actual,
          });
        }
        setMonitoringData(mockData.reverse());
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitPrediction = async () => {
    if (!newPrediction.predicted || !newPrediction.actual) {
      setError('Please enter both predicted and actual values');
      return;
    }

    const predicted = parseFloat(newPrediction.predicted);
    const actual = parseFloat(newPrediction.actual);

    if (isNaN(predicted) || isNaN(actual)) {
      setError('Please enter valid numeric values');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await mlPipelineService.monitorPrediction(
        predicted,
        actual,
        newPrediction.timestamp
      );

      if (response.success) {
        // Add to monitoring data
        const newData: MonitoringData = {
          predicted,
          actual,
          timestamp: newPrediction.timestamp,
          error: Math.abs(predicted - actual),
          relativeError: Math.abs(predicted - actual) / actual,
        };
        
        setMonitoringData(prev => [...prev, newData]);
        
        // Reset form
        setNewPrediction({
          predicted: '',
          actual: '',
          timestamp: new Date().toISOString().slice(0, 16),
        });

        // Show drift warning if detected
        if (response.data.drift_warning) {
          setError(`Warning: ${response.data.drift_warning.message}`);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit prediction');
    } finally {
      setSubmitting(false);
    }
  };

  const calculateStats = () => {
    if (monitoringData.length === 0) return null;

    const errors = monitoringData.map(d => d.error);
    const relativeErrors = monitoringData.map(d => d.relativeError);
    
    const meanError = errors.reduce((a, b) => a + b, 0) / errors.length;
    const rmse = Math.sqrt(errors.reduce((a, b) => a + b * b, 0) / errors.length);
    const meanRelativeError = relativeErrors.reduce((a, b) => a + b, 0) / relativeErrors.length;
    
    // Calculate R²
    const actualValues = monitoringData.map(d => d.actual);
    const predictedValues = monitoringData.map(d => d.predicted);
    const actualMean = actualValues.reduce((a, b) => a + b, 0) / actualValues.length;
    
    const ssRes = actualValues.reduce((sum, actual, i) => sum + Math.pow(actual - predictedValues[i], 2), 0);
    const ssTot = actualValues.reduce((sum, actual) => sum + Math.pow(actual - actualMean, 2), 0);
    const r2 = 1 - (ssRes / ssTot);

    return {
      meanError: meanError.toFixed(2),
      rmse: rmse.toFixed(2),
      meanRelativeError: (meanRelativeError * 100).toFixed(1),
      r2: r2.toFixed(3),
      sampleCount: monitoringData.length,
    };
  };

  const stats = calculateStats();

  const getPerformanceTrend = () => {
    if (performanceHistory.length < 2) return 'stable';
    
    const recent = performanceHistory[performanceHistory.length - 1];
    const previous = performanceHistory[performanceHistory.length - 2];
    
    if (recent.validation_r2 > previous.validation_r2 + 0.05) return 'improving';
    if (recent.validation_r2 < previous.validation_r2 - 0.05) return 'declining';
    return 'stable';
  };

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving': return <TrendingUp color="success" />;
      case 'declining': return <TrendingDown color="error" />;
      default: return <Timeline color="info" />;
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return 'success';
      case 'declining': return 'error';
      default: return 'info';
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Performance Monitoring
      </Typography>
      
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Monitor model performance over time and detect prediction drift. Submit actual measurements
        to track how well the model predictions match reality.
      </Typography>

      <Grid container spacing={3}>
        {/* Performance Summary */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">
                  Performance Summary
                </Typography>
                <Button
                  size="small"
                  onClick={loadPerformanceData}
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={16} /> : <Refresh />}
                >
                  Refresh
                </Button>
              </Box>

              {stats && (
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6} md={2}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">{stats.r2}</Typography>
                      <Typography variant="body2" color="text.secondary">R²</Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={2}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">{stats.rmse}</Typography>
                      <Typography variant="body2" color="text.secondary">RMSE</Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={2}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">{stats.meanError}</Typography>
                      <Typography variant="body2" color="text.secondary">Mean Error</Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={2}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">{stats.meanRelativeError}%</Typography>
                      <Typography variant="body2" color="text.secondary">Mean Rel. Error</Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={2}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h6">{stats.sampleCount}</Typography>
                      <Typography variant="body2" color="text.secondary">Samples</Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} sm={6} md={2}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1 }}>
                        {getTrendIcon(getPerformanceTrend())}
                        <Chip
                          size="small"
                          label={getPerformanceTrend()}
                          color={getTrendColor(getPerformanceTrend()) as any}
                        />
                      </Box>
                      <Typography variant="body2" color="text.secondary">Trend</Typography>
                    </Box>
                  </Grid>
                </Grid>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Add New Prediction */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Add sx={{ mr: 1, verticalAlign: 'middle' }} />
                Record Prediction
              </Typography>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Predicted Value"
                    type="number"
                    value={newPrediction.predicted}
                    onChange={(e) => setNewPrediction(prev => ({ ...prev, predicted: e.target.value }))}
                    inputProps={{ step: 0.1 }}
                  />
                </Grid>
                
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Actual Value"
                    type="number"
                    value={newPrediction.actual}
                    onChange={(e) => setNewPrediction(prev => ({ ...prev, actual: e.target.value }))}
                    inputProps={{ step: 0.1 }}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <TextField
                    fullWidth
                    label="Timestamp"
                    type="datetime-local"
                    value={newPrediction.timestamp}
                    onChange={(e) => setNewPrediction(prev => ({ ...prev, timestamp: e.target.value }))}
                    InputLabelProps={{ shrink: true }}
                  />
                </Grid>
                
                <Grid item xs={12}>
                  <Button
                    fullWidth
                    variant="contained"
                    onClick={handleSubmitPrediction}
                    disabled={submitting || !newPrediction.predicted || !newPrediction.actual}
                    startIcon={submitting ? <CircularProgress size={20} /> : <Add />}
                  >
                    {submitting ? 'Recording...' : 'Record Prediction'}
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance History Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Model Performance History
              </Typography>

              {performanceHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={performanceHistory}>
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
              ) : (
                <Alert severity="info">
                  No performance history available. Train the model to see performance metrics.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Prediction vs Actual Scatter Plot */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Predicted vs Actual
              </Typography>

              {monitoringData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart data={monitoringData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="predicted"
                      name="Predicted"
                      label={{ value: 'Predicted', position: 'insideBottom', offset: -5 }}
                    />
                    <YAxis
                      dataKey="actual"
                      name="Actual"
                      label={{ value: 'Actual', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip
                      formatter={(value: number, name: string) => [value.toFixed(2), name]}
                    />
                    <Scatter dataKey="actual" fill="#1976d2" />
                    {/* Perfect prediction line */}
                    <Line
                      type="linear"
                      dataKey="predicted"
                      stroke="#ff7300"
                      strokeDasharray="5 5"
                      dot={false}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              ) : (
                <Alert severity="info">
                  No monitoring data available. Record some predictions to see the scatter plot.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Error Over Time */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Prediction Error Over Time
              </Typography>

              {monitoringData.length > 0 ? (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={monitoringData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleString()}
                      formatter={(value: number) => [value.toFixed(2), 'Error']}
                    />
                    <Line
                      type="monotone"
                      dataKey="error"
                      stroke="#f44336"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <Alert severity="info">
                  No error data available. Record some predictions to see error trends.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Predictions Table */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent Predictions
              </Typography>

              {monitoringData.length > 0 ? (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Timestamp</TableCell>
                        <TableCell align="right">Predicted</TableCell>
                        <TableCell align="right">Actual</TableCell>
                        <TableCell align="right">Error</TableCell>
                        <TableCell align="right">Relative Error</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {monitoringData.slice(-10).reverse().map((row, index) => (
                        <TableRow key={index}>
                          <TableCell>
                            {new Date(row.timestamp).toLocaleString()}
                          </TableCell>
                          <TableCell align="right">
                            {row.predicted.toFixed(2)}
                          </TableCell>
                          <TableCell align="right">
                            {row.actual.toFixed(2)}
                          </TableCell>
                          <TableCell align="right">
                            {row.error.toFixed(2)}
                          </TableCell>
                          <TableCell align="right">
                            {(row.relativeError * 100).toFixed(1)}%
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Alert severity="info">
                  No predictions recorded yet. Use the form above to record predictions and actual measurements.
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Error Display */}
        {error && (
          <Grid item xs={12}>
            <Alert severity="error" onClose={() => setError(null)}>
              {error}
            </Alert>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default PerformanceMonitoringInterface;