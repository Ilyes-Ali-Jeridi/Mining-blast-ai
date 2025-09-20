import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Alert,
  CircularProgress,
} from '@mui/material';
import { Science as ScienceIcon } from '@mui/icons-material';

import { ScenarioGenerator } from './ScenarioGenerator';
import { ParameterExploration } from './ParameterExploration';
import { BenchmarkDataset } from './BenchmarkDataset';
import { ModelBenchmarking } from './ModelBenchmarking';
import { NoiseAnalysis } from './NoiseAnalysis';
import { syntheticService, RockType, ExplosiveType } from '../../services/syntheticService';

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
      id={`synthetic-tabpanel-${index}`}
      aria-labelledby={`synthetic-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `synthetic-tab-${index}`,
    'aria-controls': `synthetic-tabpanel-${index}`,
  };
}

export const SyntheticDataInterface: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [rockTypes, setRockTypes] = useState<RockType[]>([]);
  const [explosiveTypes, setExplosiveTypes] = useState<ExplosiveType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      setError(null);

      const [rockTypesData, explosiveTypesData] = await Promise.all([
        syntheticService.getRockTypes(),
        syntheticService.getExplosiveTypes(),
      ]);

      setRockTypes(rockTypesData);
      setExplosiveTypes(explosiveTypesData);
    } catch (err) {
      console.error('Failed to load initial data:', err);
      setError('Failed to load synthetic data configuration');
    } finally {
      setLoading(false);
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="h6" sx={{ ml: 2 }}>
          Loading synthetic data tools...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Paper sx={{ mb: 3, p: 3 }}>
        <Box display="flex" alignItems="center" mb={2}>
          <ScienceIcon sx={{ mr: 2, fontSize: 32, color: 'primary.main' }} />
          <Box>
            <Typography variant="h4" component="h1">
              Synthetic Data Generator
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Generate realistic blast scenarios for testing, validation, and model training
            </Typography>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Typography variant="body1" paragraph>
          The synthetic data generator creates realistic blast scenarios with controlled parameters
          and measurement noise. Use these tools for algorithm validation, model benchmarking,
          and parameter space exploration.
        </Typography>
      </Paper>

      <Paper sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={tabValue}
            onChange={handleTabChange}
            aria-label="synthetic data tools"
            variant="scrollable"
            scrollButtons="auto"
          >
            <Tab label="Scenario Generator" {...a11yProps(0)} />
            <Tab label="Parameter Exploration" {...a11yProps(1)} />
            <Tab label="Benchmark Dataset" {...a11yProps(2)} />
            <Tab label="Model Benchmarking" {...a11yProps(3)} />
            <Tab label="Noise Analysis" {...a11yProps(4)} />
          </Tabs>
        </Box>

        <TabPanel value={tabValue} index={0}>
          <ScenarioGenerator rockTypes={rockTypes} explosiveTypes={explosiveTypes} />
        </TabPanel>

        <TabPanel value={tabValue} index={1}>
          <ParameterExploration rockTypes={rockTypes} />
        </TabPanel>

        <TabPanel value={tabValue} index={2}>
          <BenchmarkDataset />
        </TabPanel>

        <TabPanel value={tabValue} index={3}>
          <ModelBenchmarking />
        </TabPanel>

        <TabPanel value={tabValue} index={4}>
          <NoiseAnalysis />
        </TabPanel>
      </Paper>
    </Box>
  );
};