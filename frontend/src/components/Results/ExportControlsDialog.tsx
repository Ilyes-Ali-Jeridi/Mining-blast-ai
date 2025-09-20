import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Typography,
  Box,
  Alert,
  Grid,
  Card,
  CardContent,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  CircularProgress,
  Divider,
  TextField
} from '@mui/material';
import {
  Download,
  PictureAsPdf,
  TableChart,
  Code,
  Map,
  CheckCircle,
  Warning,
  Info,
  Security
} from '@mui/icons-material';
import { BlastPlan } from '../../types';

interface ExportControlsDialogProps {
  open: boolean;
  onClose: () => void;
  onExport: (format: string, options: ExportOptions) => Promise<void>;
  blastPlan?: BlastPlan;
}

interface ExportOptions {
  format: string;
  include_safety_report: boolean;
  include_hole_details: boolean;
  include_predictions: boolean;
  include_measurements: boolean;
  include_engineer_signoff: boolean;
  filename_prefix?: string;
  coordinate_system?: string;
  units?: string;
}

const EXPORT_FORMATS = [
  {
    id: 'pdf',
    name: 'PDF Report',
    description: 'Complete blast plan report with maps and tables',
    icon: <PictureAsPdf />,
    fileExtension: '.pdf',
    features: ['Maps', 'Tables', 'Safety Report', 'Sign-off', 'Visualizations']
  },
  {
    id: 'csv',
    name: 'CSV Data',
    description: 'Hole data in comma-separated values format',
    icon: <TableChart />,
    fileExtension: '.csv',
    features: ['Hole Coordinates', 'Charge Data', 'Timing', 'Machine Readable']
  },
  {
    id: 'json',
    name: 'JSON Data',
    description: 'Complete plan data in JSON format',
    icon: <Code />,
    fileExtension: '.json',
    features: ['Complete Data', 'API Compatible', 'Structured Format', 'Metadata']
  },
  {
    id: 'geojson',
    name: 'GeoJSON',
    description: 'Geographic data for GIS integration',
    icon: <Map />,
    fileExtension: '.geojson',
    features: ['GIS Compatible', 'Spatial Data', 'Coordinate Systems', 'Mapping']
  }
];

const COORDINATE_SYSTEMS = [
  { id: 'local', name: 'Local Grid' },
  { id: 'utm', name: 'UTM' },
  { id: 'wgs84', name: 'WGS84' },
  { id: 'nad83', name: 'NAD83' }
];

const UNIT_SYSTEMS = [
  { id: 'metric', name: 'Metric (m, kg)' },
  { id: 'imperial', name: 'Imperial (ft, lbs)' }
];

export const ExportControlsDialog: React.FC<ExportControlsDialogProps> = ({
  open,
  onClose,
  onExport,
  blastPlan
}) => {
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'pdf',
    include_safety_report: true,
    include_hole_details: true,
    include_predictions: true,
    include_measurements: false,
    include_engineer_signoff: true,
    filename_prefix: '',
    coordinate_system: 'local',
    units: 'metric'
  });
  
  const [isExporting, setIsExporting] = useState(false);

  const handleOptionChange = (field: keyof ExportOptions, value: any) => {
    setExportOptions(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleExport = async () => {
    setIsExporting(true);
    
    try {
      await onExport(exportOptions.format, exportOptions);
      handleClose();
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  const handleClose = () => {
    setExportOptions({
      format: 'pdf',
      include_safety_report: true,
      include_hole_details: true,
      include_predictions: true,
      include_measurements: false,
      include_engineer_signoff: true,
      filename_prefix: '',
      coordinate_system: 'local',
      units: 'metric'
    });
    setIsExporting(false);
    onClose();
  };

  const selectedFormat = EXPORT_FORMATS.find(f => f.id === exportOptions.format);
  const canExport = blastPlan?.safety_status?.is_valid;
  const hasSignOff = blastPlan?.economic_metrics; // Placeholder for sign-off check

  const getEstimatedFileSize = (): string => {
    const holeCount = blastPlan?.holes.length || 0;
    
    switch (exportOptions.format) {
      case 'pdf':
        return `~${Math.max(1, Math.ceil(holeCount / 50))} MB`;
      case 'csv':
        return `~${Math.max(1, Math.ceil(holeCount / 1000))} KB`;
      case 'json':
        return `~${Math.max(10, Math.ceil(holeCount / 100))} KB`;
      case 'geojson':
        return `~${Math.max(5, Math.ceil(holeCount / 200))} KB`;
      default:
        return 'Unknown';
    }
  };

  const generateFilename = (): string => {
    const prefix = exportOptions.filename_prefix || 'blast_plan';
    const timestamp = new Date().toISOString().split('T')[0];
    const extension = selectedFormat?.fileExtension || '';
    return `${prefix}_${timestamp}${extension}`;
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle>
        <Box display="flex" alignItems="center" gap={1}>
          <Download color="primary" />
          Export Blast Plan
        </Box>
      </DialogTitle>

      <DialogContent>
        {!canExport ? (
          <Alert severity="error" sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Cannot Export - Safety Validation Required
            </Typography>
            <Typography variant="body2">
              This blast plan has safety violations and cannot be exported. 
              Please resolve all safety issues and obtain engineer sign-off before exporting.
            </Typography>
          </Alert>
        ) : !hasSignOff ? (
          <Alert severity="warning" sx={{ mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Engineer Sign-Off Required
            </Typography>
            <Typography variant="body2">
              This blast plan requires engineer certification before it can be exported. 
              Please complete the sign-off process first.
            </Typography>
          </Alert>
        ) : (
          <>
            {/* Export Format Selection */}
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Export Format
              </Typography>
              
              <Grid container spacing={2}>
                {EXPORT_FORMATS.map((format) => (
                  <Grid item xs={12} sm={6} key={format.id}>
                    <Card
                      variant={exportOptions.format === format.id ? "elevation" : "outlined"}
                      sx={{
                        cursor: 'pointer',
                        border: exportOptions.format === format.id ? 2 : 1,
                        borderColor: exportOptions.format === format.id ? 'primary.main' : 'divider'
                      }}
                      onClick={() => handleOptionChange('format', format.id)}
                    >
                      <CardContent>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          {format.icon}
                          <Typography variant="h6">
                            {format.name}
                          </Typography>
                        </Box>
                        
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {format.description}
                        </Typography>
                        
                        <Box display="flex" gap={0.5} flexWrap="wrap">
                          {format.features.map((feature) => (
                            <Chip
                              key={feature}
                              label={feature}
                              size="small"
                              variant="outlined"
                            />
                          ))}
                        </Box>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>

            {/* Export Options */}
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Export Options
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <List dense>
                    <ListItem sx={{ pl: 0 }}>
                      <ListItemIcon>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={exportOptions.include_safety_report}
                              onChange={(e) => handleOptionChange('include_safety_report', e.target.checked)}
                            />
                          }
                          label=""
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary="Safety Validation Report"
                        secondary="Include detailed safety checks and validation results"
                      />
                    </ListItem>
                    
                    <ListItem sx={{ pl: 0 }}>
                      <ListItemIcon>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={exportOptions.include_hole_details}
                              onChange={(e) => handleOptionChange('include_hole_details', e.target.checked)}
                            />
                          }
                          label=""
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary="Detailed Hole Information"
                        secondary="Include complete hole specifications and parameters"
                      />
                    </ListItem>
                    
                    <ListItem sx={{ pl: 0 }}>
                      <ListItemIcon>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={exportOptions.include_predictions}
                              onChange={(e) => handleOptionChange('include_predictions', e.target.checked)}
                            />
                          }
                          label=""
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary="Prediction Results"
                        secondary="Include fragmentation and PPV predictions"
                      />
                    </ListItem>
                  </List>
                </Grid>
                
                <Grid item xs={12} md={6}>
                  <List dense>
                    <ListItem sx={{ pl: 0 }}>
                      <ListItemIcon>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={exportOptions.include_measurements}
                              onChange={(e) => handleOptionChange('include_measurements', e.target.checked)}
                            />
                          }
                          label=""
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary="Measurement Data"
                        secondary="Include post-blast measurements if available"
                      />
                    </ListItem>
                    
                    <ListItem sx={{ pl: 0 }}>
                      <ListItemIcon>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={exportOptions.include_engineer_signoff}
                              onChange={(e) => handleOptionChange('include_engineer_signoff', e.target.checked)}
                              disabled={!hasSignOff}
                            />
                          }
                          label=""
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary="Engineer Sign-Off"
                        secondary="Include certification and sign-off information"
                      />
                    </ListItem>
                  </List>
                </Grid>
              </Grid>
            </Box>

            {/* Advanced Options */}
            <Box mb={3}>
              <Typography variant="h6" gutterBottom>
                Advanced Options
              </Typography>
              
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <TextField
                    fullWidth
                    label="Filename Prefix"
                    value={exportOptions.filename_prefix}
                    onChange={(e) => handleOptionChange('filename_prefix', e.target.value)}
                    placeholder="blast_plan"
                    helperText="Optional custom filename prefix"
                  />
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Coordinate System</InputLabel>
                    <Select
                      value={exportOptions.coordinate_system}
                      onChange={(e) => handleOptionChange('coordinate_system', e.target.value)}
                      label="Coordinate System"
                    >
                      {COORDINATE_SYSTEMS.map((system) => (
                        <MenuItem key={system.id} value={system.id}>
                          {system.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                
                <Grid item xs={12} md={4}>
                  <FormControl fullWidth>
                    <InputLabel>Unit System</InputLabel>
                    <Select
                      value={exportOptions.units}
                      onChange={(e) => handleOptionChange('units', e.target.value)}
                      label="Unit System"
                    >
                      {UNIT_SYSTEMS.map((system) => (
                        <MenuItem key={system.id} value={system.id}>
                          {system.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </Box>

            {/* Export Summary */}
            <Card variant="outlined">
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Export Summary
                </Typography>
                
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Box mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Format:
                      </Typography>
                      <Typography variant="body1">
                        {selectedFormat?.name} ({selectedFormat?.fileExtension})
                      </Typography>
                    </Box>
                    
                    <Box mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Estimated Size:
                      </Typography>
                      <Typography variant="body1">
                        {getEstimatedFileSize()}
                      </Typography>
                    </Box>
                  </Grid>
                  
                  <Grid item xs={12} md={6}>
                    <Box mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Filename:
                      </Typography>
                      <Typography variant="body1" fontFamily="monospace">
                        {generateFilename()}
                      </Typography>
                    </Box>
                    
                    <Box mb={1}>
                      <Typography variant="body2" color="text.secondary">
                        Holes to Export:
                      </Typography>
                      <Typography variant="body1">
                        {blastPlan?.holes.length || 0}
                      </Typography>
                    </Box>
                  </Grid>
                </Grid>
                
                <Divider sx={{ my: 2 }} />
                
                <Box display="flex" alignItems="center" gap={1}>
                  <Security color="success" />
                  <Typography variant="body2" color="success.main">
                    Plan is validated and ready for export
                  </Typography>
                </Box>
              </CardContent>
            </Card>
          </>
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={handleClose} disabled={isExporting}>
          Cancel
        </Button>
        
        {canExport && hasSignOff && (
          <Button
            onClick={handleExport}
            variant="contained"
            disabled={isExporting}
            startIcon={isExporting ? <CircularProgress size={20} /> : <Download />}
          >
            {isExporting ? 'Exporting...' : `Export ${selectedFormat?.name}`}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ExportControlsDialog;