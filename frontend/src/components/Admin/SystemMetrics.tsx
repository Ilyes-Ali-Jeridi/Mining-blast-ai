import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  CardHeader,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip
} from '@mui/material';
import {
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  Assignment as BlastIcon,
  Settings as ConfigIcon,
  Speed as PerformanceIcon
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

import { adminService, SystemMetrics as SystemMetricsType } from '../../services/adminService';

export const SystemMetrics: React.FC = () => {
  const [metrics, setMetrics] = useState<SystemMetricsType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<number>(7);

  useEffect(() => {
    loadMetrics();
  }, [selectedPeriod]);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const metricsData = await adminService.getSystemMetrics(selectedPeriod);
      setMetrics(metricsData);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load system metrics:', err);
      setError(err.message || 'Failed to load system metrics');
    } finally {
      setLoading(false);
    }
  };

  const handlePeriodChange = (event: any) => {
    setSelectedPeriod(event.target.value);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  if (!metrics) {
    return (
      <Alert severity="info" sx={{ mb: 3 }}>
        No metrics data available
      </Alert>
    );
  }

  // Prepare chart data
  const chartData = [
    {
      name: 'User Activity',
      'Total Logins': metrics.user_metrics.total_logins,
      'Unique Users': metrics.user_metrics.unique_active_users,
      'Avg/Day': metrics.user_metrics.average_logins_per_day
    },
    {
      name: 'Blast Plans',
      'Created': metrics.blast_metrics.plans_created,
      'Signed Off': metrics.blast_metrics.plans_signed_off,
      'Exported': metrics.blast_metrics.plans_exported
    }
  ];

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          System Metrics & Analytics
        </Typography>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel>Period</InputLabel>
          <Select
            value={selectedPeriod}
            label="Period"
            onChange={handlePeriodChange}
          >
            <MenuItem value={1}>1 Day</MenuItem>
            <MenuItem value={7}>7 Days</MenuItem>
            <MenuItem value={14}>14 Days</MenuItem>
            <MenuItem value={30}>30 Days</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Period Information */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Reporting Period
          </Typography>
          <Typography variant="body2" color="text.secondary">
            From: {new Date(metrics.period.start_date).toLocaleDateString()}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            To: {new Date(metrics.period.end_date).toLocaleDateString()}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Duration: {metrics.period.days} days
          </Typography>
        </CardContent>
      </Card>

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* User Metrics */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardHeader
              avatar={<PeopleIcon color="primary" />}
              title="User Activity"
              titleTypographyProps={{ variant: 'h6' }}
            />
            <CardContent>
              <Box mb={2}>
                <Typography variant="h4" color="primary">
                  {metrics.user_metrics.total_logins}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Logins
                </Typography>
              </Box>
              <Box mb={2}>
                <Typography variant="h6">
                  {metrics.user_metrics.unique_active_users}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Unique Active Users
                </Typography>
              </Box>
              <Box>
                <Typography variant="body1">
                  {metrics.user_metrics.average_logins_per_day.toFixed(1)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Average Logins/Day
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Blast Metrics */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardHeader
              avatar={<BlastIcon color="success" />}
              title="Blast Plans"
              titleTypographyProps={{ variant: 'h6' }}
            />
            <CardContent>
              <Box mb={2}>
                <Typography variant="h4" color="success.main">
                  {metrics.blast_metrics.plans_created}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Plans Created
                </Typography>
              </Box>
              <Box mb={2}>
                <Typography variant="h6">
                  {metrics.blast_metrics.plans_signed_off}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Plans Signed Off
                </Typography>
              </Box>
              <Box mb={2}>
                <Typography variant="body1">
                  {metrics.blast_metrics.plans_exported}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Plans Exported
                </Typography>
              </Box>
              <Box>
                <Typography variant="body1">
                  {metrics.blast_metrics.average_plans_per_day.toFixed(1)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Average Plans/Day
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Configuration Metrics */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardHeader
              avatar={<ConfigIcon color="warning" />}
              title="Configuration"
              titleTypographyProps={{ variant: 'h6' }}
            />
            <CardContent>
              <Box mb={2}>
                <Typography variant="h4" color="warning.main">
                  {metrics.configuration_metrics.total_changes}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Changes
                </Typography>
              </Box>
              <Box>
                <Typography variant="body1">
                  {metrics.configuration_metrics.average_changes_per_day.toFixed(1)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Average Changes/Day
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardHeader
              avatar={<PerformanceIcon color="info" />}
              title="Performance"
              titleTypographyProps={{ variant: 'h6' }}
            />
            <CardContent>
              <Box mb={2}>
                <Typography variant="h4" color="info.main">
                  {metrics.performance_metrics.average_response_time_ms?.toFixed(0) || 'N/A'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg Response Time (ms)
                </Typography>
              </Box>
              <Box>
                <Chip
                  label={
                    !metrics.performance_metrics.average_response_time_ms ? 'No Data' :
                    metrics.performance_metrics.average_response_time_ms < 500 ? 'Excellent' :
                    metrics.performance_metrics.average_response_time_ms < 1000 ? 'Good' :
                    metrics.performance_metrics.average_response_time_ms < 2000 ? 'Fair' : 'Poor'
                  }
                  color={
                    !metrics.performance_metrics.average_response_time_ms ? 'default' :
                    metrics.performance_metrics.average_response_time_ms < 500 ? 'success' :
                    metrics.performance_metrics.average_response_time_ms < 1000 ? 'primary' :
                    metrics.performance_metrics.average_response_time_ms < 2000 ? 'warning' : 'error'
                  }
                  size="small"
                />
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Activity Chart */}
      <Card sx={{ mb: 3 }}>
        <CardHeader title="Activity Overview" />
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="Total Logins" fill="#1976d2" />
              <Bar dataKey="Unique Users" fill="#2e7d32" />
              <Bar dataKey="Created" fill="#ed6c02" />
              <Bar dataKey="Signed Off" fill="#9c27b0" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Detailed Metrics Table */}
      <Card>
        <CardHeader title="Detailed Metrics" />
        <CardContent>
          <TableContainer>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Category</TableCell>
                  <TableCell>Metric</TableCell>
                  <TableCell align="right">Value</TableCell>
                  <TableCell align="right">Daily Average</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                <TableRow>
                  <TableCell rowSpan={3}>User Activity</TableCell>
                  <TableCell>Total Logins</TableCell>
                  <TableCell align="right">{metrics.user_metrics.total_logins}</TableCell>
                  <TableCell align="right">{metrics.user_metrics.average_logins_per_day.toFixed(1)}</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.user_metrics.total_logins > 0 ? 'Active' : 'Low'} 
                      color={metrics.user_metrics.total_logins > 0 ? 'success' : 'warning'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Unique Active Users</TableCell>
                  <TableCell align="right">{metrics.user_metrics.unique_active_users}</TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.user_metrics.unique_active_users > 0 ? 'Good' : 'None'} 
                      color={metrics.user_metrics.unique_active_users > 0 ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Average Logins per Day</TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell align="right">{metrics.user_metrics.average_logins_per_day.toFixed(1)}</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.user_metrics.average_logins_per_day > 1 ? 'High' : 'Low'} 
                      color={metrics.user_metrics.average_logins_per_day > 1 ? 'success' : 'warning'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>

                <TableRow>
                  <TableCell rowSpan={4}>Blast Plans</TableCell>
                  <TableCell>Plans Created</TableCell>
                  <TableCell align="right">{metrics.blast_metrics.plans_created}</TableCell>
                  <TableCell align="right">{metrics.blast_metrics.average_plans_per_day.toFixed(1)}</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.blast_metrics.plans_created > 0 ? 'Active' : 'None'} 
                      color={metrics.blast_metrics.plans_created > 0 ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Plans Signed Off</TableCell>
                  <TableCell align="right">{metrics.blast_metrics.plans_signed_off}</TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.blast_metrics.plans_signed_off > 0 ? 'Good' : 'None'} 
                      color={metrics.blast_metrics.plans_signed_off > 0 ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Plans Exported</TableCell>
                  <TableCell align="right">{metrics.blast_metrics.plans_exported}</TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.blast_metrics.plans_exported > 0 ? 'Good' : 'None'} 
                      color={metrics.blast_metrics.plans_exported > 0 ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Sign-off Rate</TableCell>
                  <TableCell align="right">
                    {metrics.blast_metrics.plans_created > 0 
                      ? `${((metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) * 100).toFixed(1)}%`
                      : 'N/A'
                    }
                  </TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell>
                    {metrics.blast_metrics.plans_created > 0 && (
                      <Chip 
                        label={
                          (metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) > 0.8 ? 'Excellent' :
                          (metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) > 0.6 ? 'Good' :
                          (metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) > 0.4 ? 'Fair' : 'Low'
                        }
                        color={
                          (metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) > 0.8 ? 'success' :
                          (metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) > 0.6 ? 'primary' :
                          (metrics.blast_metrics.plans_signed_off / metrics.blast_metrics.plans_created) > 0.4 ? 'warning' : 'error'
                        }
                        size="small"
                      />
                    )}
                  </TableCell>
                </TableRow>

                <TableRow>
                  <TableCell rowSpan={2}>Configuration</TableCell>
                  <TableCell>Total Changes</TableCell>
                  <TableCell align="right">{metrics.configuration_metrics.total_changes}</TableCell>
                  <TableCell align="right">{metrics.configuration_metrics.average_changes_per_day.toFixed(1)}</TableCell>
                  <TableCell>
                    <Chip 
                      label={metrics.configuration_metrics.total_changes > 0 ? 'Active' : 'Stable'} 
                      color={metrics.configuration_metrics.total_changes > 0 ? 'warning' : 'success'}
                      size="small"
                    />
                  </TableCell>
                </TableRow>
                <TableRow>
                  <TableCell>Change Frequency</TableCell>
                  <TableCell align="right">
                    {metrics.configuration_metrics.average_changes_per_day < 0.5 ? 'Low' :
                     metrics.configuration_metrics.average_changes_per_day < 2 ? 'Moderate' : 'High'}
                  </TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell>
                    <Chip 
                      label={
                        metrics.configuration_metrics.average_changes_per_day < 0.5 ? 'Stable' :
                        metrics.configuration_metrics.average_changes_per_day < 2 ? 'Normal' : 'High Activity'
                      }
                      color={
                        metrics.configuration_metrics.average_changes_per_day < 0.5 ? 'success' :
                        metrics.configuration_metrics.average_changes_per_day < 2 ? 'primary' : 'warning'
                      }
                      size="small"
                    />
                  </TableCell>
                </TableRow>

                <TableRow>
                  <TableCell>Performance</TableCell>
                  <TableCell>Average Response Time</TableCell>
                  <TableCell align="right">
                    {metrics.performance_metrics.average_response_time_ms?.toFixed(0) || 'N/A'} ms
                  </TableCell>
                  <TableCell align="right">-</TableCell>
                  <TableCell>
                    <Chip 
                      label={
                        !metrics.performance_metrics.average_response_time_ms ? 'No Data' :
                        metrics.performance_metrics.average_response_time_ms < 500 ? 'Excellent' :
                        metrics.performance_metrics.average_response_time_ms < 1000 ? 'Good' :
                        metrics.performance_metrics.average_response_time_ms < 2000 ? 'Fair' : 'Poor'
                      }
                      color={
                        !metrics.performance_metrics.average_response_time_ms ? 'default' :
                        metrics.performance_metrics.average_response_time_ms < 500 ? 'success' :
                        metrics.performance_metrics.average_response_time_ms < 1000 ? 'primary' :
                        metrics.performance_metrics.average_response_time_ms < 2000 ? 'warning' : 'error'
                      }
                      size="small"
                    />
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};