import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Alert,
  CircularProgress,
  Breadcrumbs,
  Link,
  Paper,
  Tabs,
  Tab
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { OptimizationInterface } from '../components/Optimization';
import { ResultsReviewInterface } from '../components/Results';
import { BlastPlan, OptimizationResult } from '../types';
import apiService from '../services/api';
import resultsService from '../services/resultsService';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div hidden={value !== index}>
    {value === index && <Box>{children}</Box>}
  </div>
);

export const OptimizationPage: React.FC = () => {
  const { blastId } = useParams<{ blastId: string }>();
  const navigate = useNavigate();
  
  const [blastPlan, setBlastPlan] = useState<BlastPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tabValue, setTabValue] = useState(0);
  const [optimizationResults, setOptimizationResults] = useState<OptimizationResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<OptimizationResult | undefined>();

  useEffect(() => {
    if (blastId) {
      loadBlastPlan(parseInt(blastId));
    } else {
      setError('No blast plan ID provided');
      setLoading(false);
    }
  }, [blastId]);

  const loadBlastPlan = async (id: number) => {
    try {
      setLoading(true);
      const response = await apiService.get<BlastPlan>(`/blast-plans/${id}`);
      
      if (response.success) {
        setBlastPlan(response.data as BlastPlan);
      } else {
        setError(response.message || 'Failed to load blast plan');
      }
    } catch (error: any) {
      console.error('Failed to load blast plan:', error);
      setError(error.response?.data?.detail || 'Failed to load blast plan');
    } finally {
      setLoading(false);
    }
  };

  const handleOptimizationComplete = (result: OptimizationResult) => {
    console.log('Optimization completed:', result);
    setOptimizationResults(prev => [...prev, result]);
    setSelectedResult(result);
    // Switch to results tab
    setTabValue(1);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleResultSelect = (result: OptimizationResult) => {
    setSelectedResult(result);
  };

  const handleExportPlan = async (result: OptimizationResult, format: string, options: any) => {
    try {
      const blob = await resultsService.exportBlastPlan(
        result.blast_plan.id || 0,
        format,
        options
      );
      
      const filename = resultsService.generateExportFilename(format, 'blast_plan');
      resultsService.downloadFile(blob, filename);
    } catch (error) {
      console.error('Export failed:', error);
      throw error;
    }
  };

  const handleSignOffPlan = async (result: OptimizationResult, signOffData: any) => {
    try {
      await resultsService.signOffBlastPlan(
        result.blast_plan.id || 0,
        signOffData
      );
      // Update the result with sign-off status
      // This would typically trigger a refresh of the results
    } catch (error) {
      console.error('Sign-off failed:', error);
      throw error;
    }
  };

  const handleModifyPlan = async (result: OptimizationResult, modifications: any) => {
    try {
      const response = await resultsService.modifyBlastPlan(
        result.blast_plan.id || 0,
        modifications
      );
      return response.data;
    } catch (error) {
      console.error('Modification failed:', error);
      throw error;
    }
  };

  const handleComparePlans = (results: OptimizationResult[]) => {
    console.log('Comparing plans:', results);
    // This could open a comparison dialog or navigate to a comparison page
  };

  const handleBlastPlanUpdate = async (updatedPlan: BlastPlan) => {
    try {
      // Save the updated blast plan
      if (blastPlan?.id) {
        const response = await apiService.put(`/blast-plans/${blastPlan.id}`, updatedPlan);
        
        if (response.success) {
          setBlastPlan(response.data as BlastPlan);
        }
      }
    } catch (error) {
      console.error('Failed to update blast plan:', error);
    }
  };

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
        <Box textAlign="center">
          <Link
            component="button"
            variant="body2"
            onClick={() => navigate('/blast-plans')}
          >
            Return to Blast Plans
          </Link>
        </Box>
      </Container>
    );
  }

  if (!blastPlan) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          Blast plan not found
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 3 }}>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/dashboard')}
        >
          Dashboard
        </Link>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate('/blast-plans')}
        >
          Blast Plans
        </Link>
        <Link
          component="button"
          variant="body2"
          onClick={() => navigate(`/blast-plans/${blastPlan.id}`)}
        >
          {`Blast Plan ${blastPlan.id}`}
        </Link>
        <Typography color="text.primary">Optimization</Typography>
      </Breadcrumbs>

      {/* Page Header */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Blast Plan Optimization
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Configure and run optimization algorithms to improve your blast plan performance.
          Monitor progress in real-time and compare results from different algorithms.
        </Typography>
        
        <Box mt={2}>
          <Typography variant="body2" color="text.secondary">
            <strong>Blast Plan ID:</strong> {blastPlan.id}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <strong>Site ID:</strong> {blastPlan.site_id}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <strong>Total Holes:</strong> {blastPlan.holes.length}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            <strong>Total Charge:</strong> {blastPlan.holes.reduce((sum, hole) => sum + hole.charge_kg, 0).toFixed(1)} kg
          </Typography>
        </Box>
      </Paper>

      {/* Main Content Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Optimization Setup" />
          <Tab label="Results Review" disabled={optimizationResults.length === 0} />
        </Tabs>
      </Paper>

      <TabPanel value={tabValue} index={0}>
        {/* Optimization Interface */}
        <OptimizationInterface
          blastPlan={blastPlan}
          onOptimizationComplete={handleOptimizationComplete}
          onBlastPlanUpdate={handleBlastPlanUpdate}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        {/* Results Review Interface */}
        {optimizationResults.length > 0 ? (
          <ResultsReviewInterface
            optimizationResults={optimizationResults}
            selectedResult={selectedResult}
            onResultSelect={handleResultSelect}
            onExportPlan={handleExportPlan}
            onSignOffPlan={handleSignOffPlan}
            onModifyPlan={handleModifyPlan}
            onComparePlans={handleComparePlans}
          />
        ) : (
          <Alert severity="info">
            No optimization results available. Run an optimization to review results here.
          </Alert>
        )}
      </TabPanel>
    </Container>
  );
};

export default OptimizationPage;