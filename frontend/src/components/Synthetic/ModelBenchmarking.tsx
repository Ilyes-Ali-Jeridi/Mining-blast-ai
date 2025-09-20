import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Grid,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  SelectChangeEvent,
} from '@mui/material';
import { Assessment as BenchmarkIcon } from '@mui/icons-material';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

import { syntheticService, ModelBenchmarkResults } from '../../services/syntheticService';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);

const AVAILABLE_MODELS = [
  { value: 'kuz_ram_default', label: 'Kuz-Ram (Default Parameters)' },
  { value: 'kuz_ram_calibrated', label: 'Kuz-Ram (Site-Calibrated)' },
];

export const ModelBenchmarking: React.FC = () => {
  const [numTestScenarios, setNumTestScenarios] = useState<number>(100);
  const [selectedModels, setSelectedModels] = useState<string[]>(['kuz_ram_default', 'kuz_ram_calibrated']);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<ModelBenchmarkResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleBenchmark = async () => {
    try {
      setLoading(true);
      setError(null);

      const benchmarkResults = await syntheticService.benchmarkModels(
        numTestScenarios,
        selectedModels
      );

      setResults(benchmarkResults);
    } catch (err) {
      console.error('Failed to benchmark models:', err);
      setError('Failed to benchmark models');
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setSelectedModels(typeof value === 'string' ? value.split(',') : value);
  };

  const formatNumber = (value: number, decimals: number = 2): string => {
    return value.toFixed(decimals);
  };

  // Prepare chart data
  const chartData = results ? {
    labels: Object.keys(results.benchmark_results),
    datasets: [
      {
        label: 'MAE (mm)',
        data: Object.values(results.benchmark_results).map(r => r.mae_mm),
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1,
      },
      {
        label: 'RMSE (mm)',
        data: Object.values(results.benchmark_results).map(r => r.rmse_mm),
        backgroundColor: 'rgba(255, 99, 132, 0.6)',
        borderColor: 'rgba(255, 99, 132, 1)',
        borderWidth: 1,
      },
    ],
  } : null;

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Model Performance Comparison',
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Error (mm)',
        },
      },
    },
  };

  const getPerformanceColor = (metric: string, value: number): 'success' | 'warning' | 'error' => {
    switch (metric) {
      case 'mae_mm':
      case 'rmse_mm':
        return value < 50 ? 'success' : value < 100 ? 'warning' : 'error';
      case 'mape_percent':
        return value < 15 ? 'success' : value < 30 ? 'warning' : 'error';
      case 'r2_score':
        return value > 0.8 ? 'success' : value > 0.6 ? 'warning' : 'error';
      default:
        return 'success';
    }
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Physics Model Benchmarking
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Compare the performance of different physics models against synthetic ground truth data.
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Benchmark Configuration
              </Typography>

              <TextField
                label="Test Scenarios"
                type="number"
                value={numTestScenarios}
                onChange={(e) => setNumTestScenarios(parseInt(e.target.value) || 100)}
                fullWidth
                sx={{ mb: 3 }}
                inputProps={{ min: 20, max: 500 }}
                helperText="Number of test scenarios to generate"
              />

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Models to Test</InputLabel>
                <Select
                  multiple
                  value={selectedModels}
                  onChange={handleModelChange}
                  label="Models to Test"
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((value) => {
                        const model = AVAILABLE_MODELS.find(m => m.value === value);
                        return (
                          <Chip
                            key={value}
                            label={model?.label || value}
                            size="small"
                          />
                        );
                      })}
                    </Box>
                  )}
                >
                  {AVAILABLE_MODELS.map((model) => (
                    <MenuItem key={model.value} value={model.value}>
                      {model.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Alert severity="info" sx={{ mb: 3 }}>
                Benchmarking will test models across different rock types and blast configurations to provide comprehensive performance metrics.
              </Alert>

              <Button
                variant="contained"
                fullWidth
                startIcon={loading ? <CircularProgress size={20} /> : <BenchmarkIcon />}
                onClick={handleBenchmark}
                disabled={loading || selectedModels.length === 0}
                size="large"
              >
                {loading ? 'Benchmarking...' : 'Start Benchmark'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Results Panel */}
        <Grid item xs={12} md={8}>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {results && (
            <Box>
              {/* Overview */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Benchmark Overview
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="h4" color="primary">
                        {results.test_scenarios}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Test Scenarios
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="h4" color="secondary">
                        {results.models_tested.length}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Models Tested
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="h4" color="info.main">
                        {Object.values(results.benchmark_results)[0]?.num_predictions || 0}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Predictions Made
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Performance Chart */}
              {chartData && (
                <Card sx={{ mb: 3 }}>
                  <CardContent>
                    <Bar data={chartData} options={chartOptions} />
                  </CardContent>
                </Card>
              )}

              {/* Detailed Results Table */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Detailed Performance Metrics
                  </Typography>
                  
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Model</TableCell>
                          <TableCell align="right">MAE (mm)</TableCell>
                          <TableCell align="right">RMSE (mm)</TableCell>
                          <TableCell align="right">MAPE (%)</TableCell>
                          <TableCell align="right">R² Score</TableCell>
                          <TableCell align="right">Predictions</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {Object.entries(results.benchmark_results).map(([modelName, metrics]) => {
                          const modelLabel = AVAILABLE_MODELS.find(m => m.value === modelName)?.label || modelName;
                          
                          return (
                            <TableRow key={modelName}>
                              <TableCell component="th" scope="row">
                                <Typography variant="body2" fontWeight="medium">
                                  {modelLabel}
                                </Typography>
                              </TableCell>
                              <TableCell align="right">
                                <Chip
                                  label={formatNumber(metrics.mae_mm)}
                                  color={getPerformanceColor('mae_mm', metrics.mae_mm)}
                                  size="small"
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Chip
                                  label={formatNumber(metrics.rmse_mm)}
                                  color={getPerformanceColor('rmse_mm', metrics.rmse_mm)}
                                  size="small"
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Chip
                                  label={formatNumber(metrics.mape_percent, 1)}
                                  color={getPerformanceColor('mape_percent', metrics.mape_percent)}
                                  size="small"
                                />
                              </TableCell>
                              <TableCell align="right">
                                <Chip
                                  label={formatNumber(metrics.r2_score, 3)}
                                  color={getPerformanceColor('r2_score', metrics.r2_score)}
                                  size="small"
                                />
                              </TableCell>
                              <TableCell align="right">
                                {metrics.num_predictions}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" color="text.secondary">
                      <strong>Metrics Explanation:</strong>
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      • MAE: Mean Absolute Error - Average absolute difference between predicted and true values
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      • RMSE: Root Mean Square Error - Square root of average squared differences
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      • MAPE: Mean Absolute Percentage Error - Average percentage error
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      • R²: Coefficient of determination - Proportion of variance explained by the model
                    </Typography>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          )}

          {!results && !loading && (
            <Card>
              <CardContent>
                <Typography variant="body1" color="text.secondary" textAlign="center">
                  Select models to test and click "Start Benchmark" to compare physics model performance.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};