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
  LinearProgress,
  Chip,
  Divider,
} from '@mui/material';
import { Dataset as DatasetIcon, Download as DownloadIcon } from '@mui/icons-material';

import { syntheticService, BenchmarkDataset as BenchmarkDatasetType } from '../../services/syntheticService';

export const BenchmarkDataset: React.FC = () => {
  const [numScenarios, setNumScenarios] = useState<number>(100);
  const [testSplit, setTestSplit] = useState<number>(0.2);
  const [validationSplit, setValidationSplit] = useState<number>(0.1);
  const [loading, setLoading] = useState(false);
  const [dataset, setDataset] = useState<BenchmarkDatasetType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setError(null);

      const generatedDataset = await syntheticService.generateBenchmarkDataset(
        numScenarios,
        testSplit,
        validationSplit
      );

      setDataset(generatedDataset);
    } catch (err) {
      console.error('Failed to generate benchmark dataset:', err);
      setError('Failed to generate benchmark dataset');
    } finally {
      setLoading(false);
    }
  };

  const formatPercentage = (value: number): string => {
    return (value * 100).toFixed(1) + '%';
  };

  const formatNumber = (value: number, decimals: number = 1): string => {
    return value.toFixed(decimals);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Benchmark Dataset Generation
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Generate comprehensive datasets for model training, validation, and testing with proper splits and quality assessment.
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Dataset Configuration
              </Typography>

              <TextField
                label="Total Scenarios"
                type="number"
                value={numScenarios}
                onChange={(e) => setNumScenarios(parseInt(e.target.value) || 100)}
                fullWidth
                sx={{ mb: 2 }}
                inputProps={{ min: 50, max: 1000 }}
                helperText="Total number of scenarios to generate"
              />

              <TextField
                label="Test Split"
                type="number"
                value={testSplit}
                onChange={(e) => setTestSplit(parseFloat(e.target.value) || 0.2)}
                fullWidth
                sx={{ mb: 2 }}
                inputProps={{ min: 0.1, max: 0.3, step: 0.05 }}
                helperText="Fraction for test set (0.1-0.3)"
              />

              <TextField
                label="Validation Split"
                type="number"
                value={validationSplit}
                onChange={(e) => setValidationSplit(parseFloat(e.target.value) || 0.1)}
                fullWidth
                sx={{ mb: 3 }}
                inputProps={{ min: 0.05, max: 0.2, step: 0.05 }}
                helperText="Fraction for validation set (0.05-0.2)"
              />

              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Dataset Splits Preview:
                </Typography>
                <Typography variant="body2">
                  • Training: {Math.round(numScenarios * (1 - testSplit - validationSplit))} scenarios
                </Typography>
                <Typography variant="body2">
                  • Validation: {Math.round(numScenarios * validationSplit)} scenarios
                </Typography>
                <Typography variant="body2">
                  • Test: {Math.round(numScenarios * testSplit)} scenarios
                </Typography>
              </Box>

              <Button
                variant="contained"
                fullWidth
                startIcon={loading ? <CircularProgress size={20} /> : <DatasetIcon />}
                onClick={handleGenerate}
                disabled={loading}
                size="large"
              >
                {loading ? 'Generating Dataset...' : 'Generate Dataset'}
              </Button>

              {loading && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    This may take a few minutes for large datasets...
                  </Typography>
                  <LinearProgress />
                </Box>
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

          {dataset && (
            <Box>
              {/* Dataset Overview */}
              <Card sx={{ mb: 3 }}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Dataset Overview
                  </Typography>
                  
                  <Grid container spacing={2} sx={{ mb: 3 }}>
                    <Grid item xs={4}>
                      <Box textAlign="center">
                        <Typography variant="h3" color="primary">
                          {dataset.dataset_splits.train}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Training
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box textAlign="center">
                        <Typography variant="h3" color="secondary">
                          {dataset.dataset_splits.validation}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Validation
                        </Typography>
                      </Box>
                    </Grid>
                    <Grid item xs={4}>
                      <Box textAlign="center">
                        <Typography variant="h3" color="info.main">
                          {dataset.dataset_splits.test}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          Test
                        </Typography>
                      </Box>
                    </Grid>
                  </Grid>

                  <Divider sx={{ my: 2 }} />

                  {/* Quality Metrics */}
                  <Typography variant="h6" gutterBottom>
                    Data Quality Assessment
                  </Typography>
                  
                  <Grid container spacing={2}>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="body2" color="text.secondary">
                        Completeness
                      </Typography>
                      <Chip
                        label={formatPercentage(dataset.validation_report.data_quality.completeness)}
                        color={dataset.validation_report.data_quality.completeness > 0.9 ? 'success' : 'warning'}
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="body2" color="text.secondary">
                        Missing Rate
                      </Typography>
                      <Chip
                        label={formatPercentage(dataset.validation_report.data_quality.missing_rate)}
                        color={dataset.validation_report.data_quality.missing_rate < 0.05 ? 'success' : 'warning'}
                        size="small"
                      />
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="body2" color="text.secondary">
                        Valid Scenarios
                      </Typography>
                      <Typography variant="h6">
                        {dataset.validation_report.valid_scenarios} / {dataset.validation_report.total_scenarios}
                      </Typography>
                    </Grid>
                    <Grid item xs={6} sm={3}>
                      <Typography variant="body2" color="text.secondary">
                        Quality Issues
                      </Typography>
                      <Typography variant="h6" color={dataset.validation_report.quality_issues > 0 ? 'warning.main' : 'success.main'}>
                        {dataset.validation_report.quality_issues}
                      </Typography>
                    </Grid>
                  </Grid>
                </CardContent>
              </Card>

              {/* Statistics */}
              {dataset.validation_report.statistics && (
                <Card sx={{ mb: 3 }}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Dataset Statistics
                    </Typography>
                    
                    <Grid container spacing={3}>
                      {dataset.validation_report.statistics.p80_mm && (
                        <Grid item xs={12} sm={4}>
                          <Typography variant="subtitle2" gutterBottom>
                            P80 Fragmentation (mm)
                          </Typography>
                          <Typography variant="body2">
                            <strong>Range:</strong> {formatNumber(dataset.validation_report.statistics.p80_mm.min)} - {formatNumber(dataset.validation_report.statistics.p80_mm.max)}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Mean:</strong> {formatNumber(dataset.validation_report.statistics.p80_mm.mean)} ± {formatNumber(dataset.validation_report.statistics.p80_mm.std)}
                          </Typography>
                        </Grid>
                      )}
                      
                      {dataset.validation_report.statistics.ppv_mm_s && (
                        <Grid item xs={12} sm={4}>
                          <Typography variant="subtitle2" gutterBottom>
                            PPV (mm/s)
                          </Typography>
                          <Typography variant="body2">
                            <strong>Range:</strong> {formatNumber(dataset.validation_report.statistics.ppv_mm_s.min, 2)} - {formatNumber(dataset.validation_report.statistics.ppv_mm_s.max, 2)}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Mean:</strong> {formatNumber(dataset.validation_report.statistics.ppv_mm_s.mean, 2)} ± {formatNumber(dataset.validation_report.statistics.ppv_mm_s.std, 2)}
                          </Typography>
                        </Grid>
                      )}
                      
                      {dataset.validation_report.statistics.powder_factor_kg_t && (
                        <Grid item xs={12} sm={4}>
                          <Typography variant="subtitle2" gutterBottom>
                            Powder Factor (kg/t)
                          </Typography>
                          <Typography variant="body2">
                            <strong>Range:</strong> {formatNumber(dataset.validation_report.statistics.powder_factor_kg_t.min, 3)} - {formatNumber(dataset.validation_report.statistics.powder_factor_kg_t.max, 3)}
                          </Typography>
                          <Typography variant="body2">
                            <strong>Mean:</strong> {formatNumber(dataset.validation_report.statistics.powder_factor_kg_t.mean, 3)} ± {formatNumber(dataset.validation_report.statistics.powder_factor_kg_t.std, 3)}
                          </Typography>
                        </Grid>
                      )}
                    </Grid>
                  </CardContent>
                </Card>
              )}

              {/* Export Information */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Export Information
                  </Typography>
                  
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Dataset files are being generated in the background. Check the server logs for completion status.
                  </Alert>
                  
                  <Typography variant="body2" color="text.secondary">
                    <strong>Export Path:</strong> {dataset.export_path}
                  </Typography>
                  
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    Generated files:
                  </Typography>
                  <Typography variant="body2" component="ul" sx={{ ml: 2 }}>
                    <li>training_dataset.json - Training set in JSON format</li>
                    <li>full_dataset.csv - Complete dataset in CSV format</li>
                  </Typography>

                  <Button
                    variant="outlined"
                    startIcon={<DownloadIcon />}
                    sx={{ mt: 2 }}
                    disabled
                  >
                    Download Dataset (Server-side export)
                  </Button>
                </CardContent>
              </Card>
            </Box>
          )}

          {!dataset && !loading && (
            <Card>
              <CardContent>
                <Typography variant="body1" color="text.secondary" textAlign="center">
                  Configure dataset parameters and click "Generate Dataset" to create a comprehensive benchmark dataset.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};