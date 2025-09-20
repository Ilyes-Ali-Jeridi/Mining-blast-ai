/**
 * ML Pipeline Page
 * 
 * Main interface for machine learning pipeline functionality including
 * fragmentation analysis, residual learning, and performance monitoring.
 */

import React, { useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  Breadcrumbs,
  Link,
} from '@mui/material';
import {
  Analytics,
  ModelTraining,
  Assessment,
  CloudUpload,
  Timeline,
  MonitorHeart,
  Storage,
} from '@mui/icons-material';

import FragmentationAnalysisInterface from '../components/MLPipeline/FragmentationAnalysisInterface';
import ResidualLearningInterface from '../components/MLPipeline/ResidualLearningInterface';
import PerformanceMonitoringInterface from '../components/MLPipeline/PerformanceMonitoringInterface';
import DataIngestionInterface from '../components/MLPipeline/DataIngestionInterface';
import ModelDiagnosticsInterface from '../components/MLPipeline/ModelDiagnosticsInterface';
import BatchJobMonitor from '../components/MLPipeline/BatchJobMonitor';
import MeasurementDataManager from '../components/MLPipeline/MeasurementDataManager';

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
      id={`ml-pipeline-tabpanel-${index}`}
      aria-labelledby={`ml-pipeline-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `ml-pipeline-tab-${index}`,
    'aria-controls': `ml-pipeline-tabpanel-${index}`,
  };
}

const MLPipelinePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Container maxWidth="xl">
      <Box sx={{ py: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 2 }}>
            <Link underline="hover" color="inherit" href="/">
              Dashboard
            </Link>
            <Typography color="text.primary">ML Pipeline</Typography>
          </Breadcrumbs>
          
          <Typography variant="h4" component="h1" gutterBottom>
            Machine Learning Pipeline
          </Typography>
          
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            Advanced machine learning tools for post-blast measurement analysis, 
            physics model corrections, and performance monitoring.
          </Typography>

          <Alert severity="info" sx={{ mb: 3 }}>
            The ML pipeline uses SAM-based fragmentation analysis and XGBoost residual learning 
            to improve prediction accuracy over time. Upload post-blast measurements to train 
            and enhance the physics-based models.
          </Alert>
        </Box>

        {/* Main Content */}
        <Paper sx={{ width: '100%' }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              aria-label="ML pipeline tabs"
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab
                icon={<Analytics />}
                label="Fragmentation Analysis"
                {...a11yProps(0)}
              />
              <Tab
                icon={<CloudUpload />}
                label="Data Ingestion"
                {...a11yProps(1)}
              />
              <Tab
                icon={<MonitorHeart />}
                label="Batch Monitor"
                {...a11yProps(2)}
              />
              <Tab
                icon={<Storage />}
                label="Data Manager"
                {...a11yProps(3)}
              />
              <Tab
                icon={<ModelTraining />}
                label="Residual Learning"
                {...a11yProps(4)}
              />
              <Tab
                icon={<Timeline />}
                label="Performance Monitoring"
                {...a11yProps(5)}
              />
              <Tab
                icon={<Assessment />}
                label="Model Diagnostics"
                {...a11yProps(6)}
              />
            </Tabs>
          </Box>

          <TabPanel value={activeTab} index={0}>
            <FragmentationAnalysisInterface />
          </TabPanel>

          <TabPanel value={activeTab} index={1}>
            <DataIngestionInterface />
          </TabPanel>

          <TabPanel value={activeTab} index={2}>
            <BatchJobMonitor />
          </TabPanel>

          <TabPanel value={activeTab} index={3}>
            <MeasurementDataManager />
          </TabPanel>

          <TabPanel value={activeTab} index={4}>
            <ResidualLearningInterface />
          </TabPanel>

          <TabPanel value={activeTab} index={5}>
            <PerformanceMonitoringInterface />
          </TabPanel>

          <TabPanel value={activeTab} index={6}>
            <ModelDiagnosticsInterface />
          </TabPanel>
        </Paper>
      </Box>
    </Container>
  );
};

export default MLPipelinePage;