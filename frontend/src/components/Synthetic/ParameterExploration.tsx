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
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
import { Explore as ExploreIcon, Download as DownloadIcon } from '@mui/icons-material';
import { Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

import { syntheticService, RockType, ParameterExplorationScenario } from '../../services/syntheticService';

ChartJS.register(CategoryScale, LinearScale, PointElement, Title, Tooltip, Legend);

interface ParameterExplorationProps {
  rockTypes: RockType[];
}

export const ParameterExploration: React.FC<ParameterExplorationProps> = ({
  rockTypes,
}) => {
  const [numScenarios, setNumScenarios] = useState<number>(50);
  const [parameterRanges, setParameterRanges] = useState({
    powder_factor: [0.2, 0.6],
    burden: [3.0, 6.0],
    bench_height: [10.0, 18.0],
    rock_factor_a: [6.0, 12.0],
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<{
    scenarios: ParameterExplorationScenario[];
    statistics: any;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleExplore = async () => {
    try {
      setLoading(true);
      setError(null);

      const explorationResults = await syntheticService.generateParameterExploration(
        numScenarios,
        parameterRanges
      );

      setResults(explorationResults);
    } catch (err) {
      console.error('Failed to generate parameter exploration:', err);
      setError('Failed to generate parameter exploration');
    } finally {
      setLoading(false);
    }
  };

  const handleParameterRangeChange = (param: string, index: number, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setParameterRanges(prev => ({
        ...prev,
        [param]: index === 0 
          ? [numValue, prev[param as keyof typeof prev][1]]
          : [prev[param as keyof typeof prev][0], numValue]
      }));
    }
  };

  const exportResults = () => {
    if (!results) return;

    const csvContent = [
      'scenario_id,rock_type,powder_factor,bench_height,rock_factor_a,true_p80,measured_p80,max_ppv',
      ...results.scenarios.map(s => 
        `${s.scenario_id},${s.rock_type},${s.powder_factor},${s.bench_height},${s.rock_factor_a},${s.true_p80},${s.measured_p80 || ''},${s.max_ppv}`
      )
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'parameter_exploration.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Prepare chart data
  const chartData = results ? {
    datasets: [
      {
        label: 'P80 vs Powder Factor',
        data: results.scenarios.map(s => ({
          x: s.powder_factor,
          y: s.true_p80,
        })),
        backgroundColor: 'rgba(54, 162, 235, 0.6)',
        borderColor: 'rgba(54, 162, 235, 1)',
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
        text: 'P80 Fragmentation vs Powder Factor',
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Powder Factor (kg/t)',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'P80 Fragmentation (mm)',
        },
      },
    },
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Parameter Space Exploration
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Systematically explore the parameter space to understand relationships between blast parameters and outcomes.
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Exploration Configuration
              </Typography>

              <TextField
                label="Number of Scenarios"
                type="number"
                value={numScenarios}
                onChange={(e) => setNumScenarios(parseInt(e.target.value) || 50)}
                fullWidth
                sx={{ mb: 3 }}
                inputProps={{ min: 10, max: 200 }}
              />

              <Typography variant="subtitle2" gutterBottom>
                Parameter Ranges
              </Typography>

              {Object.entries(parameterRanges).map(([param, range]) => (
                <Box key={param} sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    {param.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </Typography>
                  <Grid container spacing={1}>
                    <Grid item xs={6}>
                      <TextField
                        label="Min"
                        type="number"
                        size="small"
                        value={range[0]}
                        onChange={(e) => handleParameterRangeChange(param, 0, e.target.value)}
                        fullWidth
                      />
                    </Grid>
                    <Grid item xs={6}>
                      <TextField
                        label="Max"
                        type="number"
                        size="small"
                        value={range[1]}
                        onChange={(e) => handleParameterRangeChange(param, 1, e.target.value)}
                        fullWidth
                      />
                    </Grid>
                  </Grid>
                </Box>
              ))}

              <Button
                variant="contained"
                fullWidth
                startIcon={loading ? <CircularProgress size={20} /> : <ExploreIcon />}
                onClick={handleExplore}
                disabled={loading}
                size="large"
                sx={{ mt: 2 }}
              >
                {loading ? 'Exploring...' : 'Start Exploration'}
              </Button>

              {results && (
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<DownloadIcon />}
                  onClick={exportResults}
                  sx={{ mt: 1 }}
                >
                  Export Results
                </Button>
              )}
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
              {/* Statistics */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Exploration Statistics
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="h4" color="primary">
                        {results.statistics.total_scenarios}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Total Scenarios
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="h4" color="primary">
                        {new Set(results.scenarios.map(s => s.rock_type)).size}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Rock Types
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="h4" color="primary">
                        {Math.min(...results.scenarios.map(s => s.true_p80)).toFixed(0)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Min P80 (mm)
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="h4" color="primary">
                        {Math.max(...results.scenarios.map(s => s.true_p80)).toFixed(0)}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Max P80 (mm)
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Chart */}
              {chartData && (
                <Card sx={{ mb: 3 }}>
                  <CardContent>
                    <Scatter data={chartData} options={chartOptions} />
                  </CardContent>
                </Card>
              )}

              {/* Results Table */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Scenario Results (First 20)
                  </Typography>
                  <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                    <Table stickyHeader size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Scenario ID</TableCell>
                          <TableCell>Rock Type</TableCell>
                          <TableCell>Powder Factor</TableCell>
                          <TableCell>Bench Height</TableCell>
                          <TableCell>Rock Factor A</TableCell>
                          <TableCell>True P80</TableCell>
                          <TableCell>Max PPV</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {results.scenarios.slice(0, 20).map((scenario) => (
                          <TableRow key={scenario.scenario_id}>
                            <TableCell>{scenario.scenario_id}</TableCell>
                            <TableCell>
                              <Chip
                                label={scenario.rock_type.replace('_', ' ')}
                                size="small"
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>{scenario.powder_factor.toFixed(3)}</TableCell>
                            <TableCell>{scenario.bench_height.toFixed(1)}</TableCell>
                            <TableCell>{scenario.rock_factor_a.toFixed(1)}</TableCell>
                            <TableCell>{scenario.true_p80.toFixed(1)}</TableCell>
                            <TableCell>{scenario.max_ppv.toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </CardContent>
              </Card>
            </Box>
          )}

          {!results && !loading && (
            <Card>
              <CardContent>
                <Typography variant="body1" color="text.secondary" textAlign="center">
                  Configure parameter ranges and click "Start Exploration" to generate scenarios across the parameter space.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};