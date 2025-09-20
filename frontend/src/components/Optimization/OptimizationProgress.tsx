import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Button,
  Grid,
  Chip,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Collapse,
  Divider
} from '@mui/material';
import {
  PlayArrow,
  Stop,
  Refresh,
  ExpandMore,
  ExpandLess,
  CheckCircle,
  Error,
  Cancel,
  Timer
} from '@mui/icons-material';
import { OptimizationProgress as OptimizationProgressType, OptimizationSession } from '../../types';
import { useOptimizationWebSocket } from '../../hooks/useOptimizationWebSocket';

interface OptimizationProgressProps {
  session: OptimizationSession | null;
  onCancel?: () => void;
  onRestart?: () => void;
  showDetails?: boolean;
}

interface AlgorithmProgress {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  iterations?: number;
  best_objective?: number;
  runtime?: number;
  progress_percentage?: number;
}

export const OptimizationProgressComponent: React.FC<OptimizationProgressProps> = ({
  session,
  onCancel,
  onRestart,
  showDetails = true
}) => {
  const [currentProgress, setCurrentProgress] = useState<OptimizationProgressType | null>(null);
  const [algorithmProgress, setAlgorithmProgress] = useState<AlgorithmProgress[]>([]);
  const [showDetailedProgress, setShowDetailedProgress] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);

  const {
    isConnected,
    isConnecting,
    error: wsError,
    cancelOptimization
  } = useOptimizationWebSocket({
    optimizationId: session?.optimization_id || null,
    onProgress: (progress) => {
      setCurrentProgress(progress);
      updateAlgorithmProgress(progress);
    },
    onCompleted: (result) => {
      console.log('Optimization completed:', result);
      // Handle completion
    },
    onFailed: (error) => {
      console.error('Optimization failed:', error);
      // Handle failure
    },
    onCancelled: () => {
      console.log('Optimization cancelled');
      // Handle cancellation
    }
  });

  // Update elapsed time
  useEffect(() => {
    if (session?.status === 'running') {
      const interval = setInterval(() => {
        const startTime = new Date(session.started_at).getTime();
        const now = new Date().getTime();
        setElapsedTime(Math.floor((now - startTime) / 1000));
      }, 1000);

      return () => clearInterval(interval);
    }
  }, [session?.status, session?.started_at]);

  const updateAlgorithmProgress = (progress: OptimizationProgressType) => {
    if (!progress.algorithm) return;

    setAlgorithmProgress(prev => {
      const existing = prev.find(a => a.name === progress.algorithm);
      if (existing) {
        return prev.map(a => 
          a.name === progress.algorithm
            ? {
                ...a,
                status: progress.status === 'running' ? 'running' : 
                       progress.status === 'completed' ? 'completed' : 
                       progress.status === 'failed' ? 'failed' : a.status,
                iterations: progress.iteration,
                best_objective: progress.best_objective,
                progress_percentage: progress.progress_percentage
              }
            : a
        );
      } else {
        return [...prev, {
          name: progress.algorithm || 'unknown',
          status: 'running',
          iterations: progress.iteration,
          best_objective: progress.best_objective,
          progress_percentage: progress.progress_percentage || 0
        }];
      }
    });
  };

  const handleCancel = async () => {
    if (session?.status === 'running') {
      const success = cancelOptimization();
      if (success && onCancel) {
        onCancel();
      }
    }
  };

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle color="success" />;
      case 'failed':
        return <Error color="error" />;
      case 'cancelled':
        return <Cancel color="warning" />;
      case 'running':
        return <Timer color="primary" />;
      default:
        return <Timer color="disabled" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'failed':
        return 'error';
      case 'cancelled':
        return 'warning';
      case 'running':
        return 'primary';
      default:
        return 'default';
    }
  };

  if (!session) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Optimization Progress
          </Typography>
          <Typography color="text.secondary">
            No optimization session active
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6">
            Optimization Progress
          </Typography>
          <Box display="flex" gap={1}>
            {session.status === 'running' && (
              <Button
                variant="outlined"
                color="error"
                startIcon={<Stop />}
                onClick={handleCancel}
                size="small"
              >
                Cancel
              </Button>
            )}
            {(session.status === 'completed' || session.status === 'failed' || session.status === 'cancelled') && onRestart && (
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={onRestart}
                size="small"
              >
                Restart
              </Button>
            )}
          </Box>
        </Box>

        {/* Connection Status */}
        {session.status === 'running' && (
          <Box mb={2}>
            <Chip
              size="small"
              label={isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}
              color={isConnected ? 'success' : isConnecting ? 'warning' : 'error'}
              variant="outlined"
            />
          </Box>
        )}

        {/* WebSocket Error */}
        {wsError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Connection error: {wsError}
          </Alert>
        )}

        {/* Overall Status */}
        <Grid container spacing={2} mb={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Box display="flex" alignItems="center" gap={1}>
              {getStatusIcon(session.status)}
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Status
                </Typography>
                <Chip
                  label={session.status.toUpperCase()}
                  color={getStatusColor(session.status) as any}
                  size="small"
                />
              </Box>
            </Box>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Typography variant="body2" color="text.secondary">
              Elapsed Time
            </Typography>
            <Typography variant="h6">
              {formatTime(elapsedTime)}
            </Typography>
          </Grid>

          {currentProgress && (
            <>
              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">
                  Current Algorithm
                </Typography>
                <Typography variant="body1">
                  {currentProgress.algorithm || 'N/A'}
                </Typography>
              </Grid>

              <Grid item xs={12} sm={6} md={3}>
                <Typography variant="body2" color="text.secondary">
                  Best Objective
                </Typography>
                <Typography variant="h6">
                  {currentProgress.best_objective?.toFixed(2) || 'N/A'}
                </Typography>
              </Grid>
            </>
          )}
        </Grid>

        {/* Overall Progress Bar */}
        {session.status === 'running' && currentProgress && (
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
              <Typography variant="body2">
                Overall Progress
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {currentProgress.progress_percentage?.toFixed(1) || 0}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={currentProgress.progress_percentage || 0}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
        )}

        {/* Current Message */}
        {currentProgress?.message && (
          <Alert severity="info" sx={{ mb: 2 }}>
            {currentProgress.message}
          </Alert>
        )}

        {/* Detailed Progress */}
        {showDetails && algorithmProgress.length > 0 && (
          <Box>
            <Box display="flex" alignItems="center" mb={1}>
              <Typography variant="subtitle2">
                Algorithm Progress
              </Typography>
              <IconButton
                size="small"
                onClick={() => setShowDetailedProgress(!showDetailedProgress)}
              >
                {showDetailedProgress ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            </Box>

            <Collapse in={showDetailedProgress}>
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Algorithm</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell align="right">Iterations</TableCell>
                      <TableCell align="right">Best Objective</TableCell>
                      <TableCell align="right">Progress</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {algorithmProgress.map((algo) => (
                      <TableRow key={algo.name}>
                        <TableCell>{algo.name}</TableCell>
                        <TableCell>
                          <Chip
                            label={algo.status}
                            color={getStatusColor(algo.status) as any}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {algo.iterations || '-'}
                        </TableCell>
                        <TableCell align="right">
                          {algo.best_objective?.toFixed(2) || '-'}
                        </TableCell>
                        <TableCell align="right">
                          {algo.progress_percentage ? `${algo.progress_percentage.toFixed(1)}%` : '-'}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </Collapse>
          </Box>
        )}

        {/* Session Info */}
        <Box mt={2}>
          <Divider sx={{ mb: 1 }} />
          <Typography variant="caption" color="text.secondary">
            Session ID: {session.optimization_id}
          </Typography>
        </Box>
      </CardContent>
    </Card>
  );
};

export default OptimizationProgressComponent;