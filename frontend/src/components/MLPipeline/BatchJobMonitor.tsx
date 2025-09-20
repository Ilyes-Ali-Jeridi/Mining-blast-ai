/**
 * Batch Job Monitor Component
 * 
 * Monitors and displays the status of batch processing jobs for measurement data ingestion.
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  CircularProgress,
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  Grid,
  Tooltip,
} from '@mui/material';
import {
  Refresh,
  Cancel,
  ExpandMore,
  ExpandLess,
  CheckCircle,
  Error,
  Schedule,
  PlayArrow,
  Stop,
  PhotoCamera,
  GraphicEq,
  Visibility,
  Download,
} from '@mui/icons-material';

import mlPipelineService from '../../services/mlPipelineService';

interface BatchJobStatus {
  job_id: string;
  blast_record_id: number;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'partial';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  total_items: number;
  processed_items: number;
  successful_items: number;
  failed_items: number;
  progress_percentage: number;
  error_summary?: string;
  item_details: Array<{
    item_id: string;
    item_type: 'fragmentation_image' | 'ppv_file';
    filename: string;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    error?: string;
    processing_start?: string;
    processing_end?: string;
  }>;
}

interface BatchJobResults {
  job_id: string;
  blast_record_id: number;
  status: string;
  summary: {
    total_items: number;
    successful_items: number;
    failed_items: number;
    fragmentation_measurements: number;
    ppv_measurements: number;
  };
  results: {
    fragmentation: Array<{
      measurement_id: number;
      filename: string;
      p80_mm: number;
      quality: string;
      confidence_score: number;
    }>;
    ppv: Array<{
      measurement_id: number;
      filename: string;
      peak_ppv: number;
      quality: string;
      confidence_score: number;
    }>;
    errors: Array<{
      filename: string;
      item_type: string;
      error: string;
    }>;
  };
  completed_at: string;
}

const BatchJobMonitor: React.FC = () => {
  const [jobs, setJobs] = useState<BatchJobStatus[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());
  const [selectedJob, setSelectedJob] = useState<string | null>(null);
  const [jobResults, setJobResults] = useState<BatchJobResults | null>(null);
  const [resultsDialogOpen, setResultsDialogOpen] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await mlPipelineService.getBatchStatus(jobId);
      if (response.success) {
        return response.data;
      }
      return null;
    } catch (error) {
      console.error(`Failed to fetch status for job ${jobId}:`, error);
      return null;
    }
  }, []);

  const fetchAllJobs = useCallback(async () => {
    if (jobs.length === 0) return;

    setLoading(true);
    setError(null);

    try {
      const updatedJobs = await Promise.all(
        jobs.map(async (job) => {
          const status = await fetchJobStatus(job.job_id);
          return status || job;
        })
      );

      setJobs(updatedJobs);
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to refresh jobs');
    } finally {
      setLoading(false);
    }
  }, [jobs, fetchJobStatus]);

  const addJob = useCallback((jobId: string, blastRecordId: number) => {
    const newJob: BatchJobStatus = {
      job_id: jobId,
      blast_record_id: blastRecordId,
      status: 'pending',
      created_at: new Date().toISOString(),
      total_items: 0,
      processed_items: 0,
      successful_items: 0,
      failed_items: 0,
      progress_percentage: 0,
      item_details: [],
    };

    setJobs(prev => [newJob, ...prev]);
  }, []);

  const handleCancelJob = async (jobId: string) => {
    try {
      const response = await mlPipelineService.cancelBatchJob(jobId);
      if (response.success) {
        await fetchAllJobs();
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to cancel job');
    }
  };

  const handleViewResults = async (jobId: string) => {
    try {
      const response = await mlPipelineService.getBatchResults(jobId);
      if (response.success) {
        setJobResults(response.data);
        setSelectedJob(jobId);
        setResultsDialogOpen(true);
      }
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Failed to fetch results');
    }
  };

  const toggleJobExpansion = (jobId: string) => {
    setExpandedJobs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(jobId)) {
        newSet.delete(jobId);
      } else {
        newSet.add(jobId);
      }
      return newSet;
    });
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Schedule color="action" />;
      case 'processing':
        return <PlayArrow color="primary" />;
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'partial':
        return <Error color="warning" />;
      default:
        return <Schedule color="action" />;
    }
  };

  const getStatusColor = (status: string): 'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning' => {
    switch (status) {
      case 'pending':
        return 'default';
      case 'processing':
        return 'primary';
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'partial':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatDuration = (start?: string, end?: string) => {
    if (!start) return 'Not started';
    if (!end) return 'In progress';

    const startTime = new Date(start);
    const endTime = new Date(end);
    const duration = endTime.getTime() - startTime.getTime();
    const seconds = Math.floor(duration / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    } else {
      return `${seconds}s`;
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      const hasActiveJobs = jobs.some(job => 
        job.status === 'pending' || job.status === 'processing'
      );

      if (hasActiveJobs) {
        fetchAllJobs();
      }
    }, 5000); // Refresh every 5 seconds

    return () => clearInterval(interval);
  }, [autoRefresh, jobs, fetchAllJobs]);

  // Expose addJob function to parent components
  React.useImperativeHandle(React.forwardRef(() => null), () => ({
    addJob,
  }));

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Batch Job Monitor
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            size="small"
            onClick={() => setAutoRefresh(!autoRefresh)}
            color={autoRefresh ? 'primary' : 'default'}
          >
            Auto Refresh: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
          
          <Button
            variant="outlined"
            size="small"
            onClick={fetchAllJobs}
            disabled={loading}
            startIcon={loading ? <CircularProgress size={16} /> : <Refresh />}
          >
            Refresh
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {jobs.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              No batch jobs found. Submit a batch job from the Data Ingestion tab to see it here.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Job ID</TableCell>
                <TableCell>Blast Record</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Items</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobs.map((job) => (
                <React.Fragment key={job.job_id}>
                  <TableRow>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <IconButton
                          size="small"
                          onClick={() => toggleJobExpansion(job.job_id)}
                        >
                          {expandedJobs.has(job.job_id) ? <ExpandLess /> : <ExpandMore />}
                        </IconButton>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {job.job_id.slice(-8)}
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>{job.blast_record_id}</TableCell>
                    
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(job.status)}
                        label={job.status.toUpperCase()}
                        color={getStatusColor(job.status)}
                        size="small"
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 120 }}>
                        <LinearProgress
                          variant="determinate"
                          value={job.progress_percentage}
                          sx={{ flexGrow: 1 }}
                        />
                        <Typography variant="body2">
                          {Math.round(job.progress_percentage)}%
                        </Typography>
                      </Box>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {job.successful_items}/{job.total_items}
                        {job.failed_items > 0 && (
                          <span style={{ color: 'red' }}> ({job.failed_items} failed)</span>
                        )}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2">
                        {formatDuration(job.started_at, job.completed_at)}
                      </Typography>
                    </TableCell>
                    
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        {(job.status === 'completed' || job.status === 'partial') && (
                          <Tooltip title="View Results">
                            <IconButton
                              size="small"
                              onClick={() => handleViewResults(job.job_id)}
                            >
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                        )}
                        
                        {(job.status === 'pending' || job.status === 'processing') && (
                          <Tooltip title="Cancel Job">
                            <IconButton
                              size="small"
                              onClick={() => handleCancelJob(job.job_id)}
                              color="error"
                            >
                              <Cancel />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                  
                  <TableRow>
                    <TableCell colSpan={7} sx={{ py: 0 }}>
                      <Collapse in={expandedJobs.has(job.job_id)}>
                        <Box sx={{ p: 2, backgroundColor: 'grey.50' }}>
                          <Typography variant="subtitle2" gutterBottom>
                            Item Details
                          </Typography>
                          
                          {job.error_summary && (
                            <Alert severity="error" sx={{ mb: 2 }}>
                              {job.error_summary}
                            </Alert>
                          )}
                          
                          <List dense>
                            {job.item_details.map((item) => (
                              <ListItem key={item.item_id}>
                                <ListItemIcon>
                                  {item.item_type === 'fragmentation_image' ? (
                                    <PhotoCamera />
                                  ) : (
                                    <GraphicEq />
                                  )}
                                </ListItemIcon>
                                <ListItemText
                                  primary={item.filename}
                                  secondary={
                                    <Box>
                                      <Chip
                                        label={item.status}
                                        color={getStatusColor(item.status)}
                                        size="small"
                                        sx={{ mr: 1 }}
                                      />
                                      {item.error && (
                                        <Typography variant="caption" color="error">
                                          {item.error}
                                        </Typography>
                                      )}
                                    </Box>
                                  }
                                />
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Results Dialog */}
      <Dialog
        open={resultsDialogOpen}
        onClose={() => setResultsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Batch Job Results
          {selectedJob && (
            <Typography variant="body2" color="text.secondary">
              Job ID: {selectedJob}
            </Typography>
          )}
        </DialogTitle>
        
        <DialogContent>
          {jobResults && (
            <Grid container spacing={3}>
              <Grid item xs={12}>
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      Summary
                    </Typography>
                    <Grid container spacing={2}>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Total Items
                        </Typography>
                        <Typography variant="h6">
                          {jobResults.summary.total_items}
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Successful
                        </Typography>
                        <Typography variant="h6" color="success.main">
                          {jobResults.summary.successful_items}
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Failed
                        </Typography>
                        <Typography variant="h6" color="error.main">
                          {jobResults.summary.failed_items}
                        </Typography>
                      </Grid>
                      <Grid item xs={6} sm={3}>
                        <Typography variant="body2" color="text.secondary">
                          Success Rate
                        </Typography>
                        <Typography variant="h6">
                          {Math.round((jobResults.summary.successful_items / jobResults.summary.total_items) * 100)}%
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>

              {jobResults.results.fragmentation.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    Fragmentation Results ({jobResults.results.fragmentation.length})
                  </Typography>
                  <TableContainer component={Paper}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Filename</TableCell>
                          <TableCell>P80 (mm)</TableCell>
                          <TableCell>Quality</TableCell>
                          <TableCell>Confidence</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {jobResults.results.fragmentation.map((result) => (
                          <TableRow key={result.measurement_id}>
                            <TableCell>{result.filename}</TableCell>
                            <TableCell>{result.p80_mm.toFixed(1)}</TableCell>
                            <TableCell>
                              <Chip
                                label={result.quality}
                                color={result.quality === 'excellent' ? 'success' : 
                                       result.quality === 'good' ? 'primary' : 'default'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>{(result.confidence_score * 100).toFixed(1)}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>
              )}

              {jobResults.results.ppv.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom>
                    PPV Results ({jobResults.results.ppv.length})
                  </Typography>
                  <TableContainer component={Paper}>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Filename</TableCell>
                          <TableCell>Peak PPV (mm/s)</TableCell>
                          <TableCell>Quality</TableCell>
                          <TableCell>Confidence</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {jobResults.results.ppv.map((result) => (
                          <TableRow key={result.measurement_id}>
                            <TableCell>{result.filename}</TableCell>
                            <TableCell>{result.peak_ppv.toFixed(2)}</TableCell>
                            <TableCell>
                              <Chip
                                label={result.quality}
                                color={result.quality === 'excellent' ? 'success' : 
                                       result.quality === 'good' ? 'primary' : 'default'}
                                size="small"
                              />
                            </TableCell>
                            <TableCell>{(result.confidence_score * 100).toFixed(1)}%</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Grid>
              )}

              {jobResults.results.errors.length > 0 && (
                <Grid item xs={12}>
                  <Typography variant="h6" gutterBottom color="error">
                    Errors ({jobResults.results.errors.length})
                  </Typography>
                  <List>
                    {jobResults.results.errors.map((error, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Error color="error" />
                        </ListItemIcon>
                        <ListItemText
                          primary={error.filename}
                          secondary={error.error}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
              )}
            </Grid>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setResultsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BatchJobMonitor;