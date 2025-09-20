import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Tooltip,
  Alert,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Slider,
  Switch,
  FormControlLabel,
  Divider
} from '@mui/material';
import {
  Edit,
  Save,
  Cancel,
  Delete,
  Add,
  Refresh,
  Warning,
  Info,
  Undo
} from '@mui/icons-material';
import { BlastPlan, DrillHole } from '../../types';

interface PlanModificationPanelProps {
  blastPlan: BlastPlan;
  onSave: (modifications: PlanModifications) => Promise<void>;
  onCancel: () => void;
}

interface PlanModifications {
  modified_holes: DrillHole[];
  global_adjustments: {
    charge_multiplier?: number;
    delay_offset?: number;
    stemming_adjustment?: number;
  };
  validation_required: boolean;
}

interface HoleModification {
  hole_id: string;
  original_charge: number;
  new_charge: number;
  original_delay: number;
  new_delay: number;
  original_stemming: number;
  new_stemming: number;
  is_modified: boolean;
}

export const PlanModificationPanel: React.FC<PlanModificationPanelProps> = ({
  blastPlan,
  onSave,
  onCancel
}) => {
  const [modifications, setModifications] = useState<HoleModification[]>([]);
  const [globalAdjustments, setGlobalAdjustments] = useState({
    charge_multiplier: 1.0,
    delay_offset: 0,
    stemming_adjustment: 0.0
  });
  const [selectedHoles, setSelectedHoles] = useState<string[]>([]);
  const [bulkEditMode, setBulkEditMode] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);

  // Initialize modifications from blast plan
  useEffect(() => {
    const initialModifications = blastPlan.holes.map(hole => ({
      hole_id: hole.hole_id,
      original_charge: hole.charge_kg,
      new_charge: hole.charge_kg,
      original_delay: hole.delay_ms,
      new_delay: hole.delay_ms,
      original_stemming: hole.stemming_m,
      new_stemming: hole.stemming_m,
      is_modified: false
    }));
    setModifications(initialModifications);
  }, [blastPlan]);

  // Validate modifications and update warnings
  useEffect(() => {
    const warnings: string[] = [];
    
    modifications.forEach(mod => {
      if (mod.new_charge > 50) {
        warnings.push(`Hole ${mod.hole_id}: Charge exceeds 50kg limit`);
      }
      if (mod.new_charge < 0) {
        warnings.push(`Hole ${mod.hole_id}: Charge cannot be negative`);
      }
      if (mod.new_stemming < 0.5) {
        warnings.push(`Hole ${mod.hole_id}: Stemming below minimum 0.5m`);
      }
    });
    
    // Check delay conflicts
    const delayGroups = modifications.reduce((groups, mod) => {
      if (!groups[mod.new_delay]) groups[mod.new_delay] = [];
      groups[mod.new_delay].push(mod);
      return groups;
    }, {} as Record<number, HoleModification[]>);
    
    Object.entries(delayGroups).forEach(([delay, holes]) => {
      const totalCharge = holes.reduce((sum, hole) => sum + hole.new_charge, 0);
      if (totalCharge > 200) {
        warnings.push(`Delay ${delay}ms: Total charge ${totalCharge.toFixed(1)}kg exceeds 200kg limit`);
      }
    });
    
    setValidationWarnings(warnings);
  }, [modifications]);

  const handleHoleModification = (holeId: string, field: keyof HoleModification, value: number) => {
    setModifications(prev => prev.map(mod => {
      if (mod.hole_id === holeId) {
        const updated = { ...mod, [field]: value };
        updated.is_modified = (
          updated.new_charge !== updated.original_charge ||
          updated.new_delay !== updated.original_delay ||
          updated.new_stemming !== updated.original_stemming
        );
        return updated;
      }
      return mod;
    }));
    setHasUnsavedChanges(true);
  };

  const handleGlobalAdjustment = (field: keyof typeof globalAdjustments, value: number) => {
    setGlobalAdjustments(prev => ({ ...prev, [field]: value }));
  };

  const applyGlobalAdjustments = () => {
    setModifications(prev => prev.map(mod => {
      const newCharge = Math.max(0, mod.original_charge * globalAdjustments.charge_multiplier);
      const newDelay = Math.max(0, mod.original_delay + globalAdjustments.delay_offset);
      const newStemming = Math.max(0, mod.original_stemming + globalAdjustments.stemming_adjustment);
      
      return {
        ...mod,
        new_charge: newCharge,
        new_delay: newDelay,
        new_stemming: newStemming,
        is_modified: (
          newCharge !== mod.original_charge ||
          newDelay !== mod.original_delay ||
          newStemming !== mod.original_stemming
        )
      };
    }));
    setHasUnsavedChanges(true);
  };

  const handleBulkEdit = (field: string, value: number) => {
    if (selectedHoles.length === 0) return;
    
    setModifications(prev => prev.map(mod => {
      if (selectedHoles.includes(mod.hole_id)) {
        const updated = { ...mod, [`new_${field}`]: value };
        updated.is_modified = (
          updated.new_charge !== updated.original_charge ||
          updated.new_delay !== updated.original_delay ||
          updated.new_stemming !== updated.original_stemming
        );
        return updated;
      }
      return mod;
    }));
    setHasUnsavedChanges(true);
  };

  const resetHole = (holeId: string) => {
    setModifications(prev => prev.map(mod => {
      if (mod.hole_id === holeId) {
        return {
          ...mod,
          new_charge: mod.original_charge,
          new_delay: mod.original_delay,
          new_stemming: mod.original_stemming,
          is_modified: false
        };
      }
      return mod;
    }));
    setHasUnsavedChanges(true);
  };

  const resetAllModifications = () => {
    setModifications(prev => prev.map(mod => ({
      ...mod,
      new_charge: mod.original_charge,
      new_delay: mod.original_delay,
      new_stemming: mod.original_stemming,
      is_modified: false
    })));
    setGlobalAdjustments({
      charge_multiplier: 1.0,
      delay_offset: 0,
      stemming_adjustment: 0.0
    });
    setHasUnsavedChanges(false);
  };

  const handleSave = async () => {
    if (validationWarnings.length > 0) {
      // Could show a confirmation dialog here
      console.warn('Saving with validation warnings:', validationWarnings);
    }
    
    const modifiedHoles: DrillHole[] = modifications.map(mod => {
      const originalHole = blastPlan.holes.find(h => h.hole_id === mod.hole_id)!;
      return {
        ...originalHole,
        charge_kg: mod.new_charge,
        delay_ms: mod.new_delay,
        stemming_m: mod.new_stemming
      };
    });
    
    const planModifications: PlanModifications = {
      modified_holes: modifiedHoles,
      global_adjustments: globalAdjustments,
      validation_required: validationWarnings.length > 0
    };
    
    await onSave(planModifications);
  };

  const toggleHoleSelection = (holeId: string) => {
    setSelectedHoles(prev => 
      prev.includes(holeId) 
        ? prev.filter(id => id !== holeId)
        : [...prev, holeId]
    );
  };

  const selectAllHoles = () => {
    setSelectedHoles(modifications.map(mod => mod.hole_id));
  };

  const clearSelection = () => {
    setSelectedHoles([]);
  };

  const modifiedCount = modifications.filter(mod => mod.is_modified).length;
  const totalCharge = modifications.reduce((sum, mod) => sum + mod.new_charge, 0);
  const originalTotalCharge = modifications.reduce((sum, mod) => sum + mod.original_charge, 0);
  const chargeChange = totalCharge - originalTotalCharge;

  return (
    <Box>
      {/* Modification Summary */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Plan Modification
          </Typography>
          
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color="primary">
                  {modifiedCount}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Modified Holes
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color={chargeChange >= 0 ? "error" : "success"}>
                  {chargeChange >= 0 ? '+' : ''}{chargeChange.toFixed(1)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Charge Change (kg)
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h4">
                  {totalCharge.toFixed(1)}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Total Charge (kg)
                </Typography>
              </Box>
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Box textAlign="center">
                <Typography variant="h4" color={validationWarnings.length > 0 ? "error" : "success"}>
                  {validationWarnings.length}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Warnings
                </Typography>
              </Box>
            </Grid>
          </Grid>
          
          {validationWarnings.length > 0 && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Validation Warnings:
              </Typography>
              {validationWarnings.slice(0, 3).map((warning, index) => (
                <Typography key={index} variant="body2">
                  • {warning}
                </Typography>
              ))}
              {validationWarnings.length > 3 && (
                <Typography variant="body2">
                  ... and {validationWarnings.length - 3} more warnings
                </Typography>
              )}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Global Adjustments */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Global Adjustments
          </Typography>
          
          <Grid container spacing={3} alignItems="center">
            <Grid item xs={12} md={3}>
              <Typography variant="body2" gutterBottom>
                Charge Multiplier
              </Typography>
              <Slider
                value={globalAdjustments.charge_multiplier}
                onChange={(_, value) => handleGlobalAdjustment('charge_multiplier', value as number)}
                min={0.1}
                max={2.0}
                step={0.1}
                marks={[
                  { value: 0.5, label: '0.5x' },
                  { value: 1.0, label: '1.0x' },
                  { value: 1.5, label: '1.5x' }
                ]}
                valueLabelDisplay="auto"
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Delay Offset (ms)"
                type="number"
                value={globalAdjustments.delay_offset}
                onChange={(e) => handleGlobalAdjustment('delay_offset', Number(e.target.value))}
                inputProps={{ step: 25 }}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Stemming Adjustment (m)"
                type="number"
                value={globalAdjustments.stemming_adjustment}
                onChange={(e) => handleGlobalAdjustment('stemming_adjustment', Number(e.target.value))}
                inputProps={{ step: 0.1 }}
              />
            </Grid>
            
            <Grid item xs={12} md={3}>
              <Button
                fullWidth
                variant="outlined"
                onClick={applyGlobalAdjustments}
                startIcon={<Refresh />}
              >
                Apply to All
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Bulk Edit Controls */}
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">
              Bulk Edit ({selectedHoles.length} selected)
            </Typography>
            
            <Box display="flex" gap={1}>
              <Button size="small" onClick={selectAllHoles}>
                Select All
              </Button>
              <Button size="small" onClick={clearSelection}>
                Clear Selection
              </Button>
              <FormControlLabel
                control={
                  <Switch
                    checked={bulkEditMode}
                    onChange={(e) => setBulkEditMode(e.target.checked)}
                  />
                }
                label="Bulk Edit Mode"
              />
            </Box>
          </Box>
          
          {bulkEditMode && selectedHoles.length > 0 && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Set Charge (kg)"
                  type="number"
                  inputProps={{ step: 0.1, min: 0, max: 50 }}
                  onBlur={(e) => handleBulkEdit('charge', Number(e.target.value))}
                />
              </Grid>
              
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Set Delay (ms)"
                  type="number"
                  inputProps={{ step: 25, min: 0 }}
                  onBlur={(e) => handleBulkEdit('delay', Number(e.target.value))}
                />
              </Grid>
              
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  label="Set Stemming (m)"
                  type="number"
                  inputProps={{ step: 0.1, min: 0 }}
                  onBlur={(e) => handleBulkEdit('stemming', Number(e.target.value))}
                />
              </Grid>
            </Grid>
          )}
        </CardContent>
      </Card>

      {/* Hole Modifications Table */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Hole Modifications
          </Typography>
          
          <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
            <Table stickyHeader size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox">
                    Select
                  </TableCell>
                  <TableCell>Hole ID</TableCell>
                  <TableCell align="right">Charge (kg)</TableCell>
                  <TableCell align="right">Delay (ms)</TableCell>
                  <TableCell align="right">Stemming (m)</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {modifications.map((mod) => (
                  <TableRow 
                    key={mod.hole_id}
                    sx={{ 
                      backgroundColor: mod.is_modified ? 'warning.light' : 'inherit',
                      '&:hover': { backgroundColor: 'action.hover' }
                    }}
                  >
                    <TableCell padding="checkbox">
                      <input
                        type="checkbox"
                        checked={selectedHoles.includes(mod.hole_id)}
                        onChange={() => toggleHoleSelection(mod.hole_id)}
                      />
                    </TableCell>
                    
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {mod.hole_id}
                      </Typography>
                    </TableCell>
                    
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        value={mod.new_charge}
                        onChange={(e) => handleHoleModification(mod.hole_id, 'new_charge', Number(e.target.value))}
                        inputProps={{ step: 0.1, min: 0, max: 50 }}
                        sx={{ width: 80 }}
                      />
                      {mod.new_charge !== mod.original_charge && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          was {mod.original_charge.toFixed(1)}
                        </Typography>
                      )}
                    </TableCell>
                    
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        value={mod.new_delay}
                        onChange={(e) => handleHoleModification(mod.hole_id, 'new_delay', Number(e.target.value))}
                        inputProps={{ step: 25, min: 0 }}
                        sx={{ width: 80 }}
                      />
                      {mod.new_delay !== mod.original_delay && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          was {mod.original_delay}
                        </Typography>
                      )}
                    </TableCell>
                    
                    <TableCell align="right">
                      <TextField
                        size="small"
                        type="number"
                        value={mod.new_stemming}
                        onChange={(e) => handleHoleModification(mod.hole_id, 'new_stemming', Number(e.target.value))}
                        inputProps={{ step: 0.1, min: 0 }}
                        sx={{ width: 80 }}
                      />
                      {mod.new_stemming !== mod.original_stemming && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          was {mod.original_stemming.toFixed(1)}
                        </Typography>
                      )}
                    </TableCell>
                    
                    <TableCell>
                      {mod.is_modified ? (
                        <Chip label="Modified" color="warning" size="small" />
                      ) : (
                        <Chip label="Original" color="default" size="small" variant="outlined" />
                      )}
                    </TableCell>
                    
                    <TableCell align="center">
                      {mod.is_modified && (
                        <Tooltip title="Reset to original">
                          <IconButton
                            size="small"
                            onClick={() => resetHole(mod.hole_id)}
                          >
                            <Undo />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mt={3}>
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            onClick={resetAllModifications}
            startIcon={<Undo />}
            disabled={!hasUnsavedChanges}
          >
            Reset All
          </Button>
        </Box>
        
        <Box display="flex" gap={1}>
          <Button
            variant="outlined"
            onClick={onCancel}
            startIcon={<Cancel />}
          >
            Cancel
          </Button>
          
          <Button
            variant="contained"
            onClick={handleSave}
            startIcon={<Save />}
            disabled={!hasUnsavedChanges}
          >
            Save Modifications
          </Button>
        </Box>
      </Box>
    </Box>
  );
};

export default PlanModificationPanel;