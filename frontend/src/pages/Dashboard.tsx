import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Button,
  Paper,
} from '@mui/material';
import {
  Add as AddIcon,
  LocationOn,
  Explore,
  Assessment,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const quickActions = [
    {
      title: 'Create New Site',
      description: 'Set up a new mining site with geometry and rock properties',
      icon: <LocationOn />,
      action: () => navigate('/sites/new'),
      color: 'primary',
    },
    {
      title: 'New Blast Plan',
      description: 'Generate an optimized drill-and-blast plan',
      icon: <Explore />,
      action: () => navigate('/blast-plans/new'),
      color: 'secondary',
    },
    {
      title: 'View Reports',
      description: 'Access safety reports and export documentation',
      icon: <Assessment />,
      action: () => navigate('/reports'),
      color: 'success',
    },
  ];

  const stats = [
    { label: 'Active Sites', value: '0', color: 'primary' },
    { label: 'Blast Plans', value: '0', color: 'secondary' },
    { label: 'Safety Validations', value: '0', color: 'success' },
    { label: 'Exports Generated', value: '0', color: 'warning' },
  ];

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        Welcome to the Automated Drill-and-Blast System. Get started by creating a new site or blast plan.
      </Typography>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {stats.map((stat) => (
          <Grid item xs={12} sm={6} md={3} key={stat.label}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  {stat.label}
                </Typography>
                <Typography variant="h4" component="div">
                  {stat.value}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Quick Actions */}
      <Typography variant="h5" component="h2" gutterBottom>
        Quick Actions
      </Typography>
      <Grid container spacing={3}>
        {quickActions.map((action) => (
          <Grid item xs={12} md={4} key={action.title}>
            <Paper
              elevation={2}
              sx={{
                p: 3,
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                cursor: 'pointer',
                '&:hover': {
                  elevation: 4,
                  transform: 'translateY(-2px)',
                  transition: 'all 0.2s ease-in-out',
                },
              }}
              onClick={action.action}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                {action.icon}
                <Typography variant="h6" component="h3" sx={{ ml: 1 }}>
                  {action.title}
                </Typography>
              </Box>
              <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
                {action.description}
              </Typography>
              <Button
                variant="contained"
                color={action.color as any}
                startIcon={<AddIcon />}
                sx={{ mt: 2, alignSelf: 'flex-start' }}
              >
                Get Started
              </Button>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Recent Activity */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h5" component="h2" gutterBottom>
          Recent Activity
        </Typography>
        <Paper sx={{ p: 3 }}>
          <Typography variant="body2" color="text.secondary">
            No recent activity. Start by creating your first site or blast plan.
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
};