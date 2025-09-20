import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Grid,
  Alert,
  CircularProgress,
  Chip,
  Divider,
} from '@mui/material';
import { PlayArrow as GenerateIcon, Refresh as RefreshIcon } from '@mui/icons-material';

import { syntheticService, RockType, ExplosiveType, SyntheticScenario } from '../../services/syntheticService';

interface ScenarioGeneratorProps {
  rockTypes: RockType[];
  explosiveTypes: ExplosiveType[];
}

export const ScenarioGenerator: React.FC<ScenarioGeneratorProps> = ({
  rockTypes,
  explosiveTypes,
}) => {
  const [selectedRockType, setSelectedRockType] = useState<string>('');
  const [noiseLevel, setNoiseLevel] = useState<number>(0.15);
  const [loading, setLoading] = useState(false);
  const [scenario, setScenario] = useState<SyntheticScenario | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    try {
      setLoading(true);
      setError(null);

      const generatedScenario = await syntheticService.generateScenario(
        selectedRockType || undefined,
        noiseLevel
      );

      setScenario(generatedScenario);
    } catch (err) {
      console.error('Failed to generate scenario:', err);
      setError('Failed to generate synthetic scenario');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (value: number, decimals: number = 1): string => {
    return value.toFixed(decimals);
  };

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Single Scenario Generator
      </Typography>
      <Typography variant="body2" color="text.secondary" paragraph>
        Generate individual synthetic blast scenarios with customizable parameters and noise levels.
      </Typography>

      <Grid container spacing={3}>
        {/* Configuration Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Configuration
              </Typography>

              <FormControl fullWidth sx={{ mb: 3 }}>
                <InputLabel>Rock Type</InputLabel>
                <Select
                  value={selectedRockType}
                  label="Rock Type"
                  onChange={(e) => setSelectedRockType(e.target.value)}
                >
                  <MenuItem value="">
                    <em>Random</em>
                  </MenuItem>
                  {rockTypes.map((rockType) => (
                    <MenuItem key={rockType.value} value={rockType.value}>
                      {rockType.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Typography gutterBottom>
                Measurement Noise Level: {(noiseLevel * 100).toFixed(0)}%
              </Typography>
              <Slider
                value={noiseLevel}
                onChange={(_, value) => setNoiseLevel(value as number)}
                min={0.05}
                max={0.50}
                step={0.05}
                marks={[
                  { value: 0.05, label: '5%' },
                  { value: 0.15, label: '15%' },
                  { value: 0.30, label: '30%' },
                  { value: 0.50, label: '50%' },
                ]}
                sx={{ mb: 3 }}
              />

              <Button
                variant="contained"
                fullWidth
                startIcon={loading ? <CircularProgress size={20} /> : <GenerateIcon />}
                onClick={handleGenerate}
                disabled={loading}
                size="large"
              >
                {loading ? 'Generating...' : 'Generate Scenario'}
              </Button>

              {scenario && (
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<RefreshIcon />}
                  onClick={handleGenerate}
                  disabled={loading}
                  sx={{ mt: 1 }}
                >
                  Generate Another
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

          {scenario && (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Generated Scenario: {scenario.scenario_id}
                </Typography>

                <Grid container spacing={2}>
                  {/* Site Information */}
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Site Information
                    </Typography>
                    <Box sx={{ mb: 2 }}>
                      <Chip
                        label={scenario.site.rock_type.replace('_', ' ').toUpperCase()}
                        color="primary"
                        size="small"
                        sx={{ mb: 1 }}
                      />
                      <Typography variant="body2">
                        <strong>Dimensions:</strong> {formatNumber(scenario.site.bench_width)}m × {formatNumber(scenario.site.bench_length)}m × {formatNumber(scenario.site.bench_height)}m
                      </Typography>
                      <Typography variant="body2">
                        <strong>UCS:</strong> {formatNumber(scenario.site.ucs)} MPa
                      </Typography>
                      <Typography variant="body2">
                        <strong>Density:</strong> {formatNumber(scenario.site.density)} kg/m³
                      </Typography>
                      <Typography variant="body2">
                        <strong>Rock Factor A:</strong> {formatNumber(scenario.site.rock_factor_a)}
                      </Typography>
                    </Box>
                  </Grid>

                  {/* Blast Plan */}
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Blast Plan
                    </Typography>
                    <Typography variant="body2">
                      <strong>Holes:</strong> {scenario.blast_plan.num_holes}
                    </Typography>
                    <Typography variant="body2">
                      <strong>Total Charge:</strong> {formatNumber(scenario.blast_plan.total_charge)} kg
                    </Typography>
                    <Typography variant="body2">
                      <strong>Powder Factor:</strong> {formatNumber(scenario.blast_plan.powder_factor, 3)} kg/t
                    </Typography>
                  </Grid>

                  <Grid item xs={12}>
                    <Divider sx={{ my: 2 }} />
                  </Grid>

                  {/* Predictions vs Measurements */}
                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      True Predictions
                    </Typography>
                    <Typography variant="body2">
                      <strong>P10:</strong> {formatNumber(scenario.predictions.fragmentation.p10)} mm
                    </Typography>
                    <Typography variant="body2">
                      <strong>P50:</strong> {formatNumber(scenario.predictions.fragmentation.p50)} mm
                    </Typography>
                    <Typography variant="body2">
                      <strong>P80:</strong> {formatNumber(scenario.predictions.fragmentation.p80)} mm
                    </Typography>
                    <Typography variant="body2">
                      <strong>Mean Size:</strong> {formatNumber(scenario.predictions.fragmentation.mean_size)} mm
                    </Typography>
                    <Typography variant="body2">
                      <strong>Uniformity:</strong> {formatNumber(scenario.predictions.fragmentation.uniformity_index, 2)}
                    </Typography>
                  </Grid>

                  <Grid item xs={12} sm={6}>
                    <Typography variant="subtitle1" gutterBottom>
                      Noisy Measurements
                    </Typography>
                    {scenario.measurements.fragmentation.is_valid ? (
                      <>
                        <Typography variant="body2">
                          <strong>P10:</strong> {scenario.measurements.fragmentation.p10 ? formatNumber(scenario.measurements.fragmentation.p10) : 'N/A'} mm
                        </Typography>
                        <Typography variant="body2">
                          <strong>P50:</strong> {scenario.measurements.fragmentation.p50 ? formatNumber(scenario.measurements.fragmentation.p50) : 'N/A'} mm
                        </Typography>
                        <Typography variant="body2">
                          <strong>P80:</strong> {scenario.measurements.fragmentation.p80 ? formatNumber(scenario.measurements.fragmentation.p80) : 'N/A'} mm
                        </Typography>
                        <Typography variant="body2">
                          <strong>Quality:</strong> {scenario.measurements.fragmentation.quality ? (scenario.measurements.fragmentation.quality * 100).toFixed(0) + '%' : 'N/A'}
                        </Typography>
                        <Chip
                          label="Valid Measurement"
                          color="success"
                          size="small"
                          sx={{ mt: 1 }}
                        />
                      </>
                    ) : (
                      <Chip
                        label="Missing/Invalid Measurement"
                        color="warning"
                        size="small"
                      />
                    )}
                  </Grid>

                  {/* PPV Information */}
                  {Object.keys(scenario.predictions.ppv).length > 0 && (
                    <Grid item xs={12}>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="subtitle1" gutterBottom>
                        PPV Predictions
                      </Typography>
                      <Grid container spacing={1}>
                        {Object.entries(scenario.predictions.ppv).map(([receptorId, ppv]) => (
                          <Grid item key={receptorId}>
                            <Chip
                              label={`${receptorId}: ${formatNumber(ppv, 2)} mm/s`}
                              variant="outlined"
                              size="small"
                            />
                          </Grid>
                        ))}
                      </Grid>
                    </Grid>
                  )}
                </Grid>
              </CardContent>
            </Card>
          )}

          {!scenario && !loading && (
            <Card>
              <CardContent>
                <Typography variant="body1" color="text.secondary" textAlign="center">
                  Configure parameters and click "Generate Scenario" to create a synthetic blast scenario.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};