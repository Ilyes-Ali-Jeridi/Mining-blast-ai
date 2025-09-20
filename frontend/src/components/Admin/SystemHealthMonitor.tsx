import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  Chip,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  CheckCircle as HealthyIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  ExpandMore as ExpandMoreIcon,
  Storage as DatabaseIcon,
  Settings as ConfigIcon,
  People as UsersIcon,
  TrendingUp as ActivityIcon
} from '@mui/icons-material';

import { SystemHealth } from '../../services/adminService';

interface SystemHealthMonitorProps {
  systemHealth: SystemHealth | null;
  onRefresh: () => Promise<void>;
}

export const SystemHealthMonitor: React.FC<SystemHealthMonitorProps> = ({
  systemHealth,
  onRefresh
}) => {
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);

  useEffect(() => {
    if (systemHealth) {
      setLastRefresh(new Date());
    }
  }, [systemHealth]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setRefreshing(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <HealthyIcon color="success" />;
      case 'degraded':
      case 'warning':
        return <WarningIcon color="warning" />;
      case 'unhealthy':
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <WarningIcon color="disabled" />;
    }
  };

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
    switch (status) {
      case 'healthy':
        return 'success';
      case 'degraded':
      case 'warning':
        return 'warning';
      case 'unhealthy':
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };

  if (!systemHealth) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <Typography variant="h6" color="text.secondary">
          No health data available
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          System Health Monitor
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          {lastRefresh && (
            <Typography variant="body2" color="text.secondary">
              Last updated: {lastRefresh.toLocaleTimeString()}
            </Typography>
          )}
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </Box>
      </Box>

      {/* Overall Status */}
      <Alert 
        severity={getStatusColor(systemHealth.overall_status)}
        sx={{ mb: 3 }}
        icon={getStatusIcon(systemHealth.overall_status)}
      >
        <Typography variant="h6">
          System Status: {systemHealth.overall_status.toUpperCase()}
        </Typography>
        <Typography variant="body2">
          Last checked: {new Date(systemHealth.timestamp).toLocaleString()}
        </Typography>
      </Alert>

      {/* Component Status Grid */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {/* Database Component */}
        {systemHealth.components.database && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <DatabaseIcon />
                  <Typography variant="h6">Database</Typography>
                  <Chip 
                    label={systemHealth.components.database.status}
                    color={getStatusColor(systemHealth.components.database.status)}
                    size="small"
                  />
                </Box>
                
                {systemHealth.components.database.response_time_ms && (
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Response Time: {systemHealth.components.database.response_time_ms}ms
                  </Typography>
                )}
                
                {systemHealth.components.database.statistics && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" gutterBottom>Statistics:</Typography>
                    <Table size="small">
                      <TableBody>
                        <TableRow>
                          <TableCell>Active Configurations</TableCell>
                          <TableCell align="right">
                            {systemHealth.components.database.statistics.active_configurations}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Active Users</TableCell>
                          <TableCell align="right">
                            {systemHealth.components.database.statistics.active_users}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Total Sites</TableCell>
                          <TableCell align="right">
                            {systemHealth.components.database.statistics.total_sites}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell>Blast Records</TableCell>
                          <TableCell align="right">
                            {systemHealth.components.database.statistics.total_blast_records}
                          </TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </Box>
                )}
                
                {systemHealth.components.database.error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {systemHealth.components.database.error}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Configuration Component */}
        {systemHealth.components.configuration && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <ConfigIcon />
                  <Typography variant="h6">Configuration</Typography>
                  <Chip 
                    label={systemHealth.components.configuration.status}
                    color={getStatusColor(systemHealth.components.configuration.status)}
                    size="small"
                  />
                </Box>
                
                {systemHealth.components.configuration.all_required_configs_present && (
                  <Typography variant="body2" color="success.main">
                    ✓ All required configurations present
                  </Typography>
                )}
                
                {systemHealth.components.configuration.missing_configurations && (
                  <Box mt={2}>
                    <Typography variant="subtitle2" color="error" gutterBottom>
                      Missing Configurations:
                    </Typography>
                    {systemHealth.components.configuration.missing_configurations.map((config) => (
                      <Chip 
                        key={config}
                        label={config}
                        color="error"
                        size="small"
                        sx={{ mr: 1, mb: 1 }}
                      />
                    ))}
                  </Box>
                )}
                
                {systemHealth.components.configuration.error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {systemHealth.components.configuration.error}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* User Activity Component */}
        {systemHealth.components.user_activity && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <UsersIcon />
                  <Typography variant="h6">User Activity</Typography>
                  <Chip 
                    label={systemHealth.components.user_activity.status}
                    color={getStatusColor(systemHealth.components.user_activity.status)}
                    size="small"
                  />
                </Box>
                
                <Box mt={2}>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Recent Logins (24h): {systemHealth.components.user_activity.recent_logins_24h}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Recent Activity (1h): {systemHealth.components.user_activity.recent_activity_1h}
                  </Typography>
                </Box>
                
                {systemHealth.components.user_activity.error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {systemHealth.components.user_activity.error}
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Error Rate Component */}
        {systemHealth.components.error_rate && (
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1} mb={2}>
                  <ActivityIcon />
                  <Typography variant="h6">Error Rate</Typography>
                  <Chip 
                    label={systemHealth.components.error_rate.status}
                    color={getStatusColor(systemHealth.components.error_rate.status)}
                    size="small"
                  />
                </Box>
                
                <Box mt={2}>
                  <Typography variant="h4" color={
                    systemHealth.components.error_rate.error_rate_percent > 10 ? 'error.main' :
                    systemHealth.components.error_rate.error_rate_percent > 5 ? 'warning.main' :
                    'success.main'
                  }>
                    {systemHealth.components.error_rate.error_rate_percent}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Error Rate (Last Hour)
                  </Typography>
                  
                  <LinearProgress 
                    variant="determinate" 
                    value={Math.min(systemHealth.components.error_rate.error_rate_percent, 100)}
                    color={
                      systemHealth.components.error_rate.error_rate_percent > 10 ? 'error' :
                      systemHealth.components.error_rate.error_rate_percent > 5 ? 'warning' :
                      'success'
                    }
                    sx={{ mt: 1, mb: 2 }}
                  />
                  
                  <Typography variant="body2" color="text.secondary">
                    {systemHealth.components.error_rate.error_actions_1h} errors out of{' '}
                    {systemHealth.components.error_rate.total_actions_1h} total actions
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>

      {/* Detailed Information */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Detailed Health Information</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Component</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Details</TableCell>
                  <TableCell>Last Check</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(systemHealth.components).map(([componentName, component]) => (
                  <TableRow key={componentName}>
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={1}>
                        {getStatusIcon(component.status)}
                        <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                          {componentName.replace('_', ' ')}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip 
                        label={component.status}
                        color={getStatusColor(component.status)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      {component.error ? (
                        <Typography variant="body2" color="error">
                          {component.error}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="success.main">
                          Operating normally
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {new Date(systemHealth.timestamp).toLocaleString()}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};