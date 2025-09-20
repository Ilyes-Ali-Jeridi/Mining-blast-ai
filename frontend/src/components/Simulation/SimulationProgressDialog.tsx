/**
 * Dialog for monitoring simulation progress in real-time
 */

import React, { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  CircularProgress,
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  CheckCircle,
  Error,
  Warning,
  Info,
  Timer,
  Memory,
  Speed,
} from '@mui/icons-material';

import { SimulationJob, simulationService } from '../../services/simulationService';
import { useSimulationWebSocket, useSimulationProgress } from '../../hooks/useSimulationWebSocket';

interface SimulationProgressDialogProps {
  open: boolean;
  onClose: () => void;
  job: SimulationJob | null;
}

export const SimulationProgressDialog: React.FC<SimulationProgressDialogProps> = ({
  open,
  onClose,
  job,
}) => {
  const [currentJob, setCurrentJob] = useState<SimulationJob | null>(job);
  const [refreshing, setRefreshing] = useState(false);
  
  const webSocket = useSimulationWebSocket();
  const progressData = useSimulationProgress(webSocket);

  // Connect to WebSocket when dialog opens with a job
  useEffect(() => {
    if (open && job?.job_id) {
      webSocket.connect(job.job_id);
      setCurrentJob(job);
    } else if (!open) {
      webSocket.disconnect();
    }
    
    return () => {
      if (!open) {
        webSocket.disconnect();
      }
    };
  }, [open, job?.job_id]);

  // Refresh job data periodically
  useEffect(() => {
    if (!open || !job?.job_id) return;

    const refreshJob = async () => {
      try {
        setRefreshing(true);
        const updatedJob = await simulationService.getJob(job.job_id);
        setCurrentJob(updatedJob);
      } catch (error) {
        console.error('Failed to refresh job:', error);
      } finally {
        setRefreshing(false);
      }
    };

    // Initial refresh
    refreshJob();

    // Set up periodic refresh for running jobs
    let interval: NodeJS.Timeout | null = null;
    if (job.status === 'running') {
      interval = setInterval(refreshJob, 5000); // Refresh every 5 seconds
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [open, job?.job_id, job?.status]);

  const handleCancelSimulation = async () => {
    if (!currentJob) return;
    
    try {
      // Try WebSocket cancellation first
      webSocket.cancelSimulation();
      
      // Also send API request as backup
      await simulationService.cancelJob(currentJob.job_id);
    } catch (error) {
      console.error('Failed to cancel simulation:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'cancelled':
        return <Stop color="disabled" />;
      case 'running':
        return <CircularProgress size={20} />;
      case 'pending':
        return <Timer color="warning" />;
      default:
        return <Info />;
    }
  };

  const formatDuration = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const calculateProgress = (): number => {
    if (progressData?.progress !== undefined) {
      return progressData.progress;
    }
    
    if (currentJob) {
      return simulationService.calculateProgress(currentJob);
    }
    
    return 0;
  };

  const renderProgressSection = () => {
    const progress = calculateProgress();
    const status = progressData?.status || currentJob?.status || 'unknown';
    
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
            <Typography variant="h6">Simulation Progress</Typography>
            <Box display="flex" alignItems="center" gap={1}>
              {getStatusIcon(status)}
              <Chip
                label={simulationService.formatSimulationStatus(status as any)}
                color={simulationService.getStatusColor(status as any) as any}
                size="small"
              />
            </Box>
          </Box>
          
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2">
                {progressData?.message || `Status: ${status}`}
              </Typography>
              <Typography variant="body2">
                {progress.toFixed(1)}%
              </Typography>
            </Box>
            <LinearProgress 
              variant="determinate" 
              value={progress} 
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
          
          {progressData?.current_step && (
            <Typography variant="body2" color="text.secondary">
              Current Step: {progressData.current_step}
              {progressData.total_steps && ` (${progressData.total_steps} total)`}
            </Typography>
          )}
        </CardContent>
      </Card>
    );
  };

  const renderJobDetails = () => {
    if (!currentJob) return null;
    
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Job Details</Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">Simulation Type</Typography>
              <Typography variant="body1">
                {simulationService.formatSimulationType(currentJob.simulation_type)}
              </Typography>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">Job ID</Typography>
              <Typography variant="body1" sx={{ fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {currentJob.job_id}
              </Typography>
            </Grid>
            
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">Created</Typography>
              <Typography variant="body1">
                {new Date(currentJob.created_at).toLocaleString()}
              </Typography>
            </Grid>
            
            {currentJob.started_at && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Started</Typography>
                <Typography variant="body1">
                  {new Date(currentJob.started_at).toLocaleString()}
                </Typography>
              </Grid>
            )}
            
            {currentJob.blast_plan_id && (
              <Grid item xs={12} sm={6}>
                <Typography variant="body2" color="text.secondary">Blast Plan</Typography>
                <Typography variant="body1">{currentJob.blast_plan_id}</Typography>
              </Grid>
            )}
            
            <Grid item xs={12} sm={6}>
              <Typography variant="body2" color="text.secondary">Priority</Typography>
              <Typography variant="body1">{currentJob.priority}/10</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    );
  };

  const renderTimingInfo = () => {
    const elapsedTime = progressData?.elapsed_time || 
      (currentJob?.started_at ? (Date.now() - new Date(currentJob.started_at).getTime()) / 1000 : 0);
    
    const estimatedRemaining = progressData?.estimated_remaining;
    const totalRuntime = currentJob?.runtime_seconds;
    
    return (
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Timing Information</Typography>
          
          <List dense>
            {elapsedTime > 0 && (
              <ListItem>
                <ListItemIcon><Timer /></ListItemIcon>
                <ListItemText
                  primary="Elapsed Time"
                  secondary={formatDuration(elapsedTime)}
                />
              </ListItem>
            )}
            
            {estimatedRemaining && (
              <ListItem>
                <ListItemIcon><Speed /></ListItemIcon>
                <ListItemText
                  primary="Estimated Remaining"
                  secondary={formatDuration(estimatedRemaining)}
                />
              </ListItem>
            )}
            
            {totalRuntime && (
              <ListItem>
                <ListItemIcon><CheckCircle /></ListItemIcon>
                <ListItemText
                  primary="Total Runtime"
                  secondary={formatDuration(totalRuntime)}
                />
              </ListItem>
            )}
          </List>
        </CardContent>
      </Card>
    );
  };

  const renderConnectionStatus = () => {
    return (
      <Alert 
        severity={webSocket.isConnected ? 'success' : webSocket.error ? 'error' : 'info'}
        sx={{ mb: 2 }}
      >
        {webSocket.isConnected ? (
          'Connected to real-time updates'
        ) : webSocket.isConnecting ? (
          'Connecting to real-time updates...'
        ) : webSocket.error ? (
          `Connection error: ${webSocket.error}`
        ) : (
          'Not connected to real-time updates'
        )}
      </Alert>
    );
  };

  const renderMessages = () => {
    const messages: Array<{ type: string; message: string; timestamp?: string }> = [];
    
    // Add WebSocket messages
    if (webSocket.lastMessage) {
      messages.push({
        type: webSocket.lastMessage.type,
        message: webSocket.lastMessage.message || `${webSocket.lastMessage.type} event`,
        timestamp: webSocket.lastMessage.timestamp
      });
    }
    
    // Add job result messages
    if (currentJob?.result) {
      currentJob.result.warnings.forEach(warning => {
        messages.push({ type: 'warning', message: warning });
      });
      
      currentJob.result.errors.forEach(error => {
        messages.push({ type: 'error', message: error });
      });
    }
    
    if (messages.length === 0) return null;
    
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Messages</Typography>
          
          <List dense>
            {messages.map((msg, index) => (
              <React.Fragment key={index}>
                <ListItem>
                  <ListItemIcon>
                    {msg.type === 'error' ? <Error color="error" /> :
                     msg.type === 'warning' ? <Warning color="warning" /> :
                     <Info color="info" />}
                  </ListItemIcon>
                  <ListItemText
                    primary={msg.message}
                    secondary={msg.timestamp ? new Date(msg.timestamp).toLocaleTimeString() : undefined}
                  />
                </ListItem>
                {index < messages.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        </CardContent>
      </Card>
    );
  };

  if (!currentJob) {
    return (
      <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
        <DialogContent>
          <Typography>No simulation job selected</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose}>Close</Button>
        </DialogActions>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">Simulation Progress</Typography>
          {refreshing && <CircularProgress size={20} />}
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {renderConnectionStatus()}
        {renderProgressSection()}
        {renderJobDetails()}
        {renderTimingInfo()}
        {renderMessages()}
      </DialogContent>
      
      <DialogActions>
        {currentJob.status === 'running' && (
          <Button
            color="error"
            startIcon={<Stop />}
            onClick={handleCancelSimulation}
          >
            Cancel Simulation
          </Button>
        )}
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};