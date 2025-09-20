import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  CircularProgress,
  Grid,
  Card,
  CardContent,
  CardHeader,
  Divider
} from '@mui/material';
import {
  Settings as SettingsIcon,
  People as PeopleIcon,
  Security as SecurityIcon,
  Science as ScienceIcon,
  LocalFireDepartment as ExplosivesIcon,
  MonitorHeart as MonitorIcon,
  Assessment as MetricsIcon
} from '@mui/icons-material';

import { SystemHealthMonitor } from '../components/Admin/SystemHealthMonitor';
import { UserManagement } from '../components/Admin/UserManagement';
import { ConfigurationManager } from '../components/Admin/ConfigurationManager';
import { PhysicsCalibration } from '../components/Admin/PhysicsCalibration';
import { ExplosivesManager } from '../components/Admin/ExplosivesManager';
import { SafetyLimitsManager } from '../components/Admin/SafetyLimitsManager';
import { SystemMetrics } from '../components/Admin/SystemMetrics';
import { useAuth } from '../hooks/useAuth';
import { adminService } from '../services/adminService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`admin-tabpanel-${index}`}
      aria-labelledby={`admin-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `admin-tab-${index}`,
    'aria-controls': `admin-tabpanel-${index}`,
  };
}

export const AdminPage: React.FC = () => {
  const { user } = useAuth();
  const [tabValue, setTabValue] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [systemHealth, setSystemHealth] = useState<any>(null);

  useEffect(() => {
    // Check if user has admin access
    if (!user || user.role !== 'admin') {
      setError('Access denied. Admin privileges required.');
      setLoading(false);
      return;
    }

    // Load initial system health data
    loadSystemHealth();
  }, [user]);

  const loadSystemHealth = async () => {
    try {
      setLoading(true);
      const health = await adminService.getSystemHealth();
      setSystemHealth(health);
      setError(null);
    } catch (err: any) {
      console.error('Failed to load system health:', err);
      setError(err.message || 'Failed to load system health');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        System Administration
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Manage system configuration, users, and monitor system health.
      </Typography>

      {/* System Health Overview */}
      {systemHealth && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Box display="flex" alignItems="center" gap={1}>
                  <MonitorIcon color={systemHealth.overall_status === 'healthy' ? 'success' : 'error'} />
                  <Typography variant="h6">System Status</Typography>
                </Box>
                <Typography 
                  variant="h4" 
                  color={systemHealth.overall_status === 'healthy' ? 'success.main' : 'error.main'}
                  sx={{ textTransform: 'capitalize' }}
                >
                  {systemHealth.overall_status}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Database</Typography>
                <Typography variant="body2" color="text.secondary">
                  {systemHealth.components?.database?.statistics?.active_users || 0} Active Users
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {systemHealth.components?.database?.statistics?.total_blast_records || 0} Blast Records
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Performance</Typography>
                <Typography variant="body2" color="text.secondary">
                  DB Response: {systemHealth.components?.database?.response_time_ms || 0}ms
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Error Rate: {systemHealth.components?.error_rate?.error_rate_percent || 0}%
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>Activity</Typography>
                <Typography variant="body2" color="text.secondary">
                  Recent Logins: {systemHealth.components?.user_activity?.recent_logins_24h || 0}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Recent Actions: {systemHealth.components?.user_activity?.recent_activity_1h || 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs 
            value={tabValue} 
            onChange={handleTabChange} 
            aria-label="admin tabs"
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab 
              icon={<MonitorIcon />} 
              label="System Health" 
              {...a11yProps(0)} 
            />
            <Tab 
              icon={<MetricsIcon />} 
              label="Metrics" 
              {...a11yProps(1)} 
            />
            <Tab 
              icon={<PeopleIcon />} 
              label="User Management" 
              {...a11yProps(2)} 
            />
            <Tab 
              icon={<SettingsIcon />} 
              label="Configuration" 
              {...a11yProps(3)} 
            />
            <Tab 
              icon={<ScienceIcon />} 
              label="Physics Calibration" 
              {...a11yProps(4)} 
            />
            <Tab 
              icon={<ExplosivesIcon />} 
              label="Explosives Database" 
              {...a11yProps(5)} 
            />
            <Tab 
              icon={<SecurityIcon />} 
              label="Safety Limits" 
              {...a11yProps(6)} 
            />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <SystemHealthMonitor 
            systemHealth={systemHealth}
            onRefresh={loadSystemHealth}
          />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <SystemMetrics />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <UserManagement />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <ConfigurationManager />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <PhysicsCalibration />
        </TabPanel>

        <TabPanel value={tabValue} index={5}>
          <ExplosivesManager />
        </TabPanel>

        <TabPanel value={tabValue} index={6}>
          <SafetyLimitsManager />
        </TabPanel>
      </Paper>
    </Container>
  );
};

export default AdminPage;