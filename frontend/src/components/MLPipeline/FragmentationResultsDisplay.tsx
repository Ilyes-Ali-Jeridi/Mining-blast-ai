/**
 * Fragmentation Results Display
 * 
 * Component for displaying fragmentation analysis results with charts and statistics.
 */

import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from '@mui/material';
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

import { FragmentationAnalysisResult } from '../../services/mlPipelineService';

interface Props {
  result: FragmentationAnalysisResult;
  recommendations: string[];
}

const FragmentationResultsDisplay: React.FC<Props> = ({ result, recommendations }) => {
  // Generate size distribution data for chart
  const sizeDistributionData = [
    { size: 'P10', value: result.p10_mm, label: '10th Percentile' },
    { size: 'P50', value: result.p50_mm, label: '50th Percentile (Median)' },
    { size: 'P80', value: result.p80_mm, label: '80th Percentile' },
    { size: 'Mean', value: result.mean_size_mm, label: 'Mean Size' },
  ];

  // Generate fragmentation curve data (simplified)
  const fragmentationCurveData = [];
  for (let i = 0; i <= 100; i += 10) {
    const size = result.characteristic_size_mm * Math.pow(-Math.log(1 - i / 100), 1 / result.uniformity_index);
    fragmentationCurveData.push({
      passing: i,
      size: Math.min(size, result.p80_mm * 2), // Cap at reasonable value
    });
  }

  const formatNumber = (value: number, decimals = 1) => {
    return value.toFixed(decimals);
  };

  const getQualityColor = (quality: number) => {
    if (quality >= 0.8) return 'success';
    if (quality >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Grid container spacing={3}>
      {/* Summary Statistics */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Size Distribution Statistics
            </Typography>

            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Metric</TableCell>
                    <TableCell align="right">Value (mm)</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell>P10 (Fine)</TableCell>
                    <TableCell align="right">{formatNumber(result.p10_mm)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>P50 (Median)</TableCell>
                    <TableCell align="right">{formatNumber(result.p50_mm)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 'bold' }}>P80 (Coarse)</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                      {formatNumber(result.p80_mm)}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Mean Size</TableCell>
                    <TableCell align="right">{formatNumber(result.mean_size_mm)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Characteristic Size (Xc)</TableCell>
                    <TableCell align="right">{formatNumber(result.characteristic_size_mm)}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Uniformity Index (n)</TableCell>
                    <TableCell align="right">{formatNumber(result.uniformity_index, 2)}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Analysis Metadata */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Analysis Details
            </Typography>

            <TableContainer>
              <Table size="small">
                <TableBody>
                  <TableRow>
                    <TableCell>Fragment Count</TableCell>
                    <TableCell align="right">{result.fragment_count}</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Analyzed Area</TableCell>
                    <TableCell align="right">
                      {formatNumber(result.total_analyzed_area_mm2 / 1000000, 2)} m²
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Scale Factor</TableCell>
                    <TableCell align="right">
                      {formatNumber(result.scale_factor_mm_per_pixel, 3)} mm/pixel
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Processing Time</TableCell>
                    <TableCell align="right">
                      {new Date(result.processing_timestamp).toLocaleTimeString()}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell>Validity</TableCell>
                    <TableCell align="right">
                      <Chip
                        size="small"
                        label={result.is_valid ? 'Valid' : 'Invalid'}
                        color={result.is_valid ? 'success' : 'error'}
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Size Distribution Chart */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Size Distribution
            </Typography>

            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={sizeDistributionData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="size" />
                <YAxis label={{ value: 'Size (mm)', angle: -90, position: 'insideLeft' }} />
                <Tooltip
                  formatter={(value: number) => [`${formatNumber(value)} mm`, 'Size']}
                  labelFormatter={(label) => {
                    const item = sizeDistributionData.find(d => d.size === label);
                    return item?.label || label;
                  }}
                />
                <Bar dataKey="value" fill="#1976d2" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Fragmentation Curve */}
      <Grid item xs={12} md={6}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Fragmentation Curve
            </Typography>

            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={fragmentationCurveData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="passing"
                  label={{ value: 'Percent Passing (%)', position: 'insideBottom', offset: -5 }}
                />
                <YAxis
                  label={{ value: 'Size (mm)', angle: -90, position: 'insideLeft' }}
                  scale="log"
                  domain={['dataMin', 'dataMax']}
                />
                <Tooltip
                  formatter={(value: number) => [`${formatNumber(value)} mm`, 'Size']}
                  labelFormatter={(label) => `${label}% Passing`}
                />
                <Line
                  type="monotone"
                  dataKey="size"
                  stroke="#1976d2"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </Grid>

      {/* Quality Metrics */}
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Quality Assessment
            </Typography>

            <Grid container spacing={2}>
              <Grid item xs={12} sm={4}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color={`${getQualityColor(result.measurement_quality)}.main`}>
                    {(result.measurement_quality * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Overall Quality
                  </Typography>
                </Box>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color={`${getQualityColor(result.scale_detection_quality)}.main`}>
                    {(result.scale_detection_quality * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Scale Detection
                  </Typography>
                </Box>
              </Grid>

              <Grid item xs={12} sm={4}>
                <Box sx={{ textAlign: 'center' }}>
                  <Typography variant="h4" color={`${getQualityColor(result.segmentation_quality)}.main`}>
                    {(result.segmentation_quality * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Segmentation
                  </Typography>
                </Box>
              </Grid>
            </Grid>

            {result.quality_flags.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Quality Issues:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                  {result.quality_flags.map((flag, index) => (
                    <Chip
                      key={index}
                      label={flag}
                      size="small"
                      color="warning"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default FragmentationResultsDisplay;