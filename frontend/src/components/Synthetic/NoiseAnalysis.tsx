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
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import { Analytics as AnalyticsIcon } from '@mui/icons-material';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

import { syntheticService, NoiseAnalysis as NoiseAnalysisType } from '../../services/syntheticService';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

export const NoiseAnalysis: React.FC = () => {
  const [noiseLevels, setNoiseLevels] = useState<string>('0.05,0.10,0.20,0.30');
  const [numSamples, setNumSamples] = useState<number>(50);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<NoiseAnalysisType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    try {
      setLoading(true);
      setError(null);

      // Parse noise levels
      const levels = noiseLevels
        .split(',')
        .map(s => parseFloat(s.trim()))
        .filter(n => !isNaN(n) && n > 0 && n <= 1);

      if (levels.length === 0) {
        throw new Error('Please provide valid noise levels (0-1)');
      }

      const analysisResults = await syntheticService.analyzeNoise(
        undefined, // Use random base scenario
        levels,
        numSamples
      );

      setResults(analysisResults);
    } catch (err) {
      console.error('Failed to analyze noise:', err);
      setError(err instanceof Error ? err.message : 'Failed to analyze noise');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (value: number, decimals: number = 2): string => {
    return value.toFixed(decimals);
  };

  // Prepare chart data
  const chartData = results ? {
    labels: results.noise_analysis.map(n => `${(n.noise_level * 100).toFixed(0)}%`),
    datasets: [
      {
        label: 'Standard Deviation (mm)',
        data: results.noise_analysis.map(n => n.fragmentation.std_p80),
        borderColor: 'rgba(54, 162, 235, 1)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.1,
      },
      {
        label: 'Absolute Bias (mm)',
        data: results.noise_analysis.map(n => Math.abs(n.fragmentation.bias)),
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.1,
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
        text: 'Measurement Error vs Noise Level',
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Noise Level',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Error (mm)',
        },
      },
    },
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Measurement Noise Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Analyze how measurement noise affects the quality and reliability of synthetic data.
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Analysis Configuration
              </Typography>

              <TextField
                label="Noise Levels"
                value={noiseLevels}
                onChange={(e) => setNoiseLevels(e.target.value)}
                fullWidth
                sx={{ mb: 2 }}
                helperText="Comma-separated values (e.g., 0.05,0.10,0.20,0.30)"
                placeholder="0.05,0.10,0.20,0.30"
              />

              <TextField
                label="Samples per Noise Level"
                type="number"
                value={numSamples}
                onChange={(e) => setNumSamples(parseInt(e.target.value) || 50)}
                fullWidth
                sx={{ mb: 3 }}
                inputProps={{ min: 10, max: 200 }}
                helperText="Number of noisy measurements to generate"
              />

              <Alert severity="info" sx={{ mb: 3 }}>
                This analysis generates multiple noisy measurements from a single base scenario to understand noise effects on measurement precision and bias.
              </Alert>

              <Button
                variant="contained"
                fullWidth
                startIcon={loading ? <CircularProgress size={20} /> : <AnalyticsIcon />}
                onClick={handleAnalyze}
                disabled={loading}
                size="large"
              >
                {loading ? 'Analyzing...' : 'Analyze Noise Effects'}
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
              {/* Base Scenario Info */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Base Scenario Information
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        Scenario ID
                      </Typography>
                      <Typography variant="body1">
                        {results.base_scenario.scenario_id}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        Rock Type
                      </Typography>
                      <Chip
                        label={results.base_scenario.rock_type.replace('_', ' ').toUpperCase()}
                        size="small"
                        color="primary"
                      />
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="body2" color="text.secondary">
                        True P80
                      </Typography>
                      <Typography variant="h6" color="primary">
                        {formatNumber(results.base_scenario.true_p80, 1)} mm
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Noise Effects Chart */}
              {chartData && (
                <Card sx={{ mb: 3 }}>
                  <CardContent>
                    <Line data={chartData} options={chartOptions} />
                  </CardContent>
                </Card>
              )}

              {/* Detailed Analysis Table */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Detailed Noise Analysis
                  </Typography>
                  
                  <TableContainer component={Paper}>
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Noise Level</TableCell>
                          <TableCell align="right">Mean P80 (mm)</TableCell>
                          <TableCell align="right">Std Dev (mm)</TableCell>
                          <TableCell align="right">Bias (mm)</TableCell>
                          <TableCell align="right">Measurements</TableCell>
                          <TableCell align="right">PPV Samples</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {results.noise_analysis.map((analysis) => (
                          <TableRow key={analysis.noise_level}>
                            <TableCell>
                              <Chip
                                label={`${(analysis.noise_level * 100).toFixed(0)}%`}
                                color={analysis.noise_level <= 0.1 ? 'success' : analysis.noise_level <= 0.2 ? 'warning' : 'error'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">
                              {formatNumber(analysis.fragmentation.mean_p80, 1)}
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={formatNumber(analysis.fragmentation.std_p80, 1)}
                                color={analysis.fragmentation.std_p80 < 20 ? 'success' : analysis.fragmentation.std_p80 < 50 ? 'warning' : 'error'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={formatNumber(analysis.fragmentation.bias, 1)}
                                color={Math.abs(analysis.fragmentation.bias) < 10 ? 'success' : Math.abs(analysis.fragmentation.bias) < 25 ? 'warning' : 'error'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell align="right">
                              {analysis.fragmentation.measurements}
                            </TableCell>
                            <TableCell align="right">
                              {analysis.ppv.measurements}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>

                  <Box sx={{ mt: 3 }}>
                    <Typography variant="h6" gutterBottom>
                      Analysis Summary
                    </Typography>
                    
                    <Grid container spacing={2}>
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Precision Impact:</strong>
                        </Typography>
                        <Typography variant="body2">
                          Higher noise levels increase measurement variability (standard deviation).
                          At {(results.noise_analysis[0]?.noise_level * 100 || 0).toFixed(0)}% noise: ±{formatNumber(results.noise_analysis[0]?.fragmentation.std_p80 || 0, 1)} mm
                        </Typography>
                        <Typography variant="body2">
                          At {(results.noise_analysis[results.noise_analysis.length - 1]?.noise_level * 100 || 0).toFixed(0)}% noise: ±{formatNumber(results.noise_analysis[results.noise_analysis.length - 1]?.fragmentation.std_p80 || 0, 1)} mm
                        </Typography>
                      </Grid>
                      
                      <Grid item xs={12} sm={6}>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Bias Impact:</strong>
                        </Typography>
                        <Typography variant="body2">
                          Systematic bias in measurements can shift the mean away from true values.
                          Maximum observed bias: {formatNumber(Math.max(...results.noise_analysis.map(a => Math.abs(a.fragmentation.bias))), 1)} mm
                        </Typography>
                      </Grid>
                    </Grid>

                    <Alert severity="warning" sx={{ mt: 2 }}>
                      <Typography variant="body2">
                        <strong>Recommendation:</strong> For reliable measurements, keep noise levels below 15% 
                        and implement quality control measures to detect and filter outliers.
                      </Typography>
                    </Alert>
                  </Box>
                </CardContent>
              </Card>
            </Box>
          )}

          {!results && !loading && (
            <Card>
              <CardContent>
                <Typography variant="body1" color="text.secondary" textAlign="center">
                  Configure noise levels and click "Analyze Noise Effects" to understand how measurement uncertainty affects data quality.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};