import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  LinearProgress,
  Tooltip,
  IconButton,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions
} from '@mui/material';
import {
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  ExpandMore,
  Info,
  Security,
  Refresh,
  Visibility
} from '@mui/icons-material';
import { SafetyStatus, BlastPlan } from '../../types';

interface SafetyValidationDisplayProps {
  safetyStatus?: SafetyStatus;
  blastPlan?: BlastPlan;
  onRevalidate?: () => Promise<void>;
  showDetailedChecks?: boolean;
  isRevalidating?: boolean;
}

interface SafetyCheck {
  check_type: string;
  description: string;
  status: 'pass' | 'fail' | 'warning';
  value: number;
  limit: number;
  unit: string;
  margin_percent: number;
  details?: string;
}

interface SafetyViolation {
  violation_type: string;
  severity: 'critical' | 'major' | 'minor';
  description: string;
  affected_holes?: string[];
  current_value: number;
  limit_value: number;
  unit: string;
  recommendation: string;
}

export const SafetyValidationDisplay: React.FC<SafetyValidationDisplayProps> = ({
  safetyStatus,
  blastPlan,
  onRevalidate,
  showDetailedChecks = true,
  isRevalidating = false
}) => {
  const [detailsDialogOpen, setDetailsDialogOpen] = useState(false);
  const [selectedViolation, setSelectedViolation] = useState<SafetyViolation | null>(null);

  // Mock safety checks data (in real implementation, this would come from the API)
  const mockSafetyChecks: SafetyCheck[] = [
    {
      check_type: 'charge_per_hole',
      description: 'Maximum charge per hole',
      status: 'pass',
      value: 45.2,
      limit: 50.0,
      unit: 'kg',
      margin_percent: 9.6,
      details: 'All holes within regulatory limit'
    },
    {
      check_type: 'charge_per_delay',
      description: 'Maximum charge per delay',
      status: 'pass',
      value: 180.5,
      limit: 200.0,
      unit: 'kg',
      margin_percent: 9.75,
      details: 'All delay groups within limit'
    },
    {
      check_type: 'powder_factor',
      description: 'Powder factor range',
      status: 'pass',
      value: 0.85,
      limit: 1.5,
      unit: 'kg/t',
      margin_percent: 43.3,
      details: 'Within acceptable range (0.05 - 1.5 kg/t)'
    },
    {
      check_type: 'ppv_receptors',
      description: 'PPV at sensitive receptors',
      status: safetyStatus?.is_valid ? 'pass' : 'fail',
      value: safetyStatus?.is_valid ? 4.2 : 6.8,
      limit: 5.0,
      unit: 'mm/s',
      margin_percent: safetyStatus?.is_valid ? 16.0 : -36.0,
      details: safetyStatus?.is_valid ? 'All receptors within PPV limits' : 'Receptor R001 exceeds limit'
    },
    {
      check_type: 'burden_spacing',
      description: 'Burden and spacing constraints',
      status: 'pass',
      value: 3.5,
      limit: 2.0,
      unit: 'm',
      margin_percent: 75.0,
      details: 'All holes meet minimum burden/spacing requirements'
    }
  ];

  // Mock violations data
  const mockViolations: SafetyViolation[] = safetyStatus?.is_valid ? [] : [
    {
      violation_type: 'ppv_exceeded',
      severity: 'critical',
      description: 'PPV limit exceeded at sensitive receptor',
      affected_holes: ['H001', 'H002', 'H003'],
      current_value: 6.8,
      limit_value: 5.0,
      unit: 'mm/s',
      recommendation: 'Reduce charge in holes H001-H003 or increase delay timing'
    }
  ];

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'major': return 'warning';
      case 'minor': return 'info';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass': return <CheckCircle color="success" />;
      case 'fail': return <ErrorIcon color="error" />;
      case 'warning': return <Warning color="warning" />;
      default: return <Info />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass': return 'success';
      case 'fail': return 'error';
      case 'warning': return 'warning';
      default: return 'default';
    }
  };

  const formatMargin = (margin: number): string => {
    const sign = margin >= 0 ? '+' : '';
    return `${sign}${margin.toFixed(1)}%`;
  };

  const getMarginColor = (margin: number): string => {
    if (margin >= 10) return 'success.main';
    if (margin >= 0) return 'warning.main';
    return 'error.main';
  };

  const handleViolationDetails = (violation: SafetyViolation) => {
    setSelectedViolation(violation);
    setDetailsDialogOpen(true);
  };

  if (!safetyStatus) {
    return (
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Safety Validation
          </Typography>
          <Alert severity="info">
            No safety validation data available. Run safety validation to see results here.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Box>
      {/* Overall Safety Status */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Safety Validation Status
            </Typography>
            
            {onRevalidate && (
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={onRevalidate}
                disabled={isRevalidating}
                size="small"
              >
                {isRevalidating ? 'Revalidating...' : 'Revalidate'}
              </Button>
            )}
          </Box>

          {isRevalidating && <LinearProgress sx={{ mb: 2 }} />}

          <Box display="flex" alignItems="center" gap={2} mb={2}>
            {getStatusIcon(safetyStatus.is_valid ? 'pass' : 'fail')}
            <Typography variant="h5" color={safetyStatus.is_valid ? 'success.main' : 'error.main'}>
              {safetyStatus.is_valid ? 'SAFE TO EXPORT' : 'UNSAFE - CANNOT EXPORT'}
            </Typography>
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Box textAlign="center">
                <Typography variant="h3" color="success.main">
                  {mockSafetyChecks.filter(c => c.status === 'pass').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Checks Passed
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Box textAlign="center">
                <Typography variant="h3" color="error.main">
                  {mockViolations.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Violations
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Box textAlign="center">
                <Typography variant="h3" color="warning.main">
                  {mockSafetyChecks.filter(c => c.status === 'warning').length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Warnings
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Safety Violations */}
      {mockViolations.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom color="error">
              Safety Violations ({mockViolations.length})
            </Typography>
            
            {mockViolations.map((violation, index) => (
              <Alert 
                key={index}
                severity={getSeverityColor(violation.severity) as any}
                sx={{ mb: 1 }}
                action={
                  <IconButton
                    size="small"
                    onClick={() => handleViolationDetails(violation)}
                  >
                    <Visibility />
                  </IconButton>
                }
              >
                <Box>
                  <Typography variant="subtitle2" gutterBottom>
                    {violation.description}
                  </Typography>
                  <Typography variant="body2">
                    Current: {violation.current_value} {violation.unit} | 
                    Limit: {violation.limit_value} {violation.unit}
                  </Typography>
                  {violation.affected_holes && (
                    <Typography variant="body2" color="text.secondary">
                      Affected holes: {violation.affected_holes.join(', ')}
                    </Typography>
                  )}
                </Box>
              </Alert>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Detailed Safety Checks */}
      {showDetailedChecks && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Detailed Safety Checks
            </Typography>
            
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Status</TableCell>
                    <TableCell>Check</TableCell>
                    <TableCell align="right">Current Value</TableCell>
                    <TableCell align="right">Limit</TableCell>
                    <TableCell align="right">Safety Margin</TableCell>
                    <TableCell>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {mockSafetyChecks.map((check, index) => (
                    <TableRow key={index}>
                      <TableCell>
                        <Chip
                          icon={getStatusIcon(check.status)}
                          label={check.status.toUpperCase()}
                          color={getStatusColor(check.status) as any}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {check.description}
                        </Typography>
                      </TableCell>
                      
                      <TableCell align="right">
                        <Typography variant="body2">
                          {check.value.toFixed(1)} {check.unit}
                        </Typography>
                      </TableCell>
                      
                      <TableCell align="right">
                        <Typography variant="body2">
                          {check.limit.toFixed(1)} {check.unit}
                        </Typography>
                      </TableCell>
                      
                      <TableCell align="right">
                        <Typography 
                          variant="body2" 
                          fontWeight="medium"
                          color={getMarginColor(check.margin_percent)}
                        >
                          {formatMargin(check.margin_percent)}
                        </Typography>
                      </TableCell>
                      
                      <TableCell>
                        <Tooltip title={check.details || ''}>
                          <Typography variant="body2" color="text.secondary">
                            {check.details ? 
                              (check.details.length > 30 ? 
                                `${check.details.substring(0, 30)}...` : 
                                check.details
                              ) : 
                              'No details'
                            }
                          </Typography>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* Safety Margins Summary */}
      <Card sx={{ mt: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Safety Margins Summary
          </Typography>
          
          <Grid container spacing={2}>
            {mockSafetyChecks.map((check, index) => (
              <Grid item xs={12} sm={6} md={4} key={index}>
                <Box 
                  p={2} 
                  border={1} 
                  borderColor="divider" 
                  borderRadius={1}
                  bgcolor={check.status === 'fail' ? 'error.light' : 'background.paper'}
                >
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {check.check_type.replace('_', ' ').toUpperCase()}
                  </Typography>
                  
                  <Box display="flex" alignItems="center" gap={1}>
                    {getStatusIcon(check.status)}
                    <Typography 
                      variant="h6" 
                      color={getMarginColor(check.margin_percent)}
                    >
                      {formatMargin(check.margin_percent)}
                    </Typography>
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary">
                    {check.value.toFixed(1)} / {check.limit.toFixed(1)} {check.unit}
                  </Typography>
                </Box>
              </Grid>
            ))}
          </Grid>
        </CardContent>
      </Card>

      {/* Violation Details Dialog */}
      <Dialog
        open={detailsDialogOpen}
        onClose={() => setDetailsDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box display="flex" alignItems="center" gap={1}>
            <ErrorIcon color="error" />
            Safety Violation Details
          </Box>
        </DialogTitle>
        
        <DialogContent>
          {selectedViolation && (
            <Box>
              <Typography variant="h6" gutterBottom>
                {selectedViolation.description}
              </Typography>
              
              <Grid container spacing={2} sx={{ mb: 2 }}>
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Severity:
                  </Typography>
                  <Chip
                    label={selectedViolation.severity.toUpperCase()}
                    color={getSeverityColor(selectedViolation.severity) as any}
                    size="small"
                  />
                </Grid>
                
                <Grid item xs={6}>
                  <Typography variant="body2" color="text.secondary">
                    Violation Type:
                  </Typography>
                  <Typography variant="body1">
                    {selectedViolation.violation_type.replace('_', ' ')}
                  </Typography>
                </Grid>
              </Grid>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Current Value:
                </Typography>
                <Typography variant="h6" color="error">
                  {selectedViolation.current_value} {selectedViolation.unit}
                </Typography>
              </Box>
              
              <Box mb={2}>
                <Typography variant="body2" color="text.secondary">
                  Limit Value:
                </Typography>
                <Typography variant="h6">
                  {selectedViolation.limit_value} {selectedViolation.unit}
                </Typography>
              </Box>
              
              {selectedViolation.affected_holes && (
                <Box mb={2}>
                  <Typography variant="body2" color="text.secondary">
                    Affected Holes:
                  </Typography>
                  <Box display="flex" gap={0.5} flexWrap="wrap">
                    {selectedViolation.affected_holes.map(hole => (
                      <Chip key={hole} label={hole} size="small" variant="outlined" />
                    ))}
                  </Box>
                </Box>
              )}
              
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Recommendation:
                </Typography>
                <Alert severity="info">
                  {selectedViolation.recommendation}
                </Alert>
              </Box>
            </Box>
          )}
        </DialogContent>
        
        <DialogActions>
          <Button onClick={() => setDetailsDialogOpen(false)}>
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SafetyValidationDisplay;