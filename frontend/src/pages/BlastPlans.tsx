import React, { useState } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Stack,
} from '@mui/material';
import { Add as AddIcon, Map as MapIcon, Tune as TuneIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { BlastPlanMap } from '../components/Map/BlastPlanMap';
import { BlastPlan, DrillHole } from '../types';

// Sample data for demonstration
const sampleBlastPlan: BlastPlan = {
  id: 1,
  site_id: 1,
  holes: [
    {
      hole_id: 'H001',
      coordinates: { x: 0, y: 0, z: 100 },
      depth: 12,
      diameter: 150,
      charge_kg: 25,
      stemming_m: 3,
      delay_ms: 0,
      explosive_type: 'ANFO',
    },
    {
      hole_id: 'H002',
      coordinates: { x: 5, y: 0, z: 100 },
      depth: 12,
      diameter: 150,
      charge_kg: 30,
      stemming_m: 3,
      delay_ms: 25,
      explosive_type: 'ANFO',
    },
    {
      hole_id: 'H003',
      coordinates: { x: 10, y: 0, z: 100 },
      depth: 12,
      diameter: 150,
      charge_kg: 28,
      stemming_m: 3,
      delay_ms: 50,
      explosive_type: 'Emulsion',
    },
    {
      hole_id: 'H004',
      coordinates: { x: 0, y: 5, z: 100 },
      depth: 12,
      diameter: 150,
      charge_kg: 32,
      stemming_m: 3,
      delay_ms: 75,
      explosive_type: 'ANFO',
    },
    {
      hole_id: 'H005',
      coordinates: { x: 5, y: 5, z: 100 },
      depth: 12,
      diameter: 150,
      charge_kg: 27,
      stemming_m: 3,
      delay_ms: 100,
      explosive_type: 'Emulsion',
    },
    {
      hole_id: 'H006',
      coordinates: { x: 10, y: 5, z: 100 },
      depth: 12,
      diameter: 150,
      charge_kg: 29,
      stemming_m: 3,
      delay_ms: 125,
      explosive_type: 'Slurry',
    },
  ],
  predicted_fragmentation: {
    p10: 15,
    p50: 45,
    p80: 85,
    mean: 52,
    uniformity_index: 1.25,
    distribution_type: 'rosin_rammler',
  },
  safety_status: {
    is_valid: true,
    violations: [],
    safety_margin: {
      charge_per_hole: 0.8,
      ppv_limit: 0.6,
    },
  },
  economic_metrics: {
    total_charge: 171,
    total_holes: 6,
    powder_factor: 0.45,
    estimated_cost: 1250,
  },
};

const sampleReceptors = [
  {
    id: 'R001',
    name: 'Office Building',
    coordinates: { x: 50, y: 50, z: 100 },
    ppv_limit: 5.0,
  },
  {
    id: 'R002',
    name: 'Equipment Shed',
    coordinates: { x: -30, y: 20, z: 100 },
    ppv_limit: 10.0,
  },
];

export const BlastPlans: React.FC = () => {
  const navigate = useNavigate();
  const [selectedHole, setSelectedHole] = useState<DrillHole | null>(null);
  const [showMap, setShowMap] = useState(false);

  const handleHoleSelect = (hole: DrillHole) => {
    setSelectedHole(hole);
  };

  const handleHoleEdit = (hole: DrillHole) => {
    console.log('Editing hole:', hole);
    // In a real app, this would update the blast plan
  };

  const handleMeasurement = (distance: number, area: number) => {
    console.log('Measurement:', { distance, area });
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Blast Plans
        </Typography>
        <Stack direction="row" spacing={2}>
          <Button
            variant={showMap ? "contained" : "outlined"}
            startIcon={<MapIcon />}
            onClick={() => setShowMap(!showMap)}
          >
            {showMap ? 'Hide Map' : 'Show Map'}
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/blast-plans/new')}
          >
            Create New Plan
          </Button>
        </Stack>
      </Box>

      <Grid container spacing={3}>
        {/* Blast Plan List */}
        <Grid item xs={12} md={showMap ? 4 : 12}>
          <Stack spacing={2}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Sample Blast Plan #001
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                  <Chip
                    label={sampleBlastPlan.safety_status?.is_valid ? "Safe" : "Unsafe"}
                    color={sampleBlastPlan.safety_status?.is_valid ? "success" : "error"}
                    size="small"
                  />
                  <Chip
                    label={`${sampleBlastPlan.holes.length} holes`}
                    variant="outlined"
                    size="small"
                  />
                  <Chip
                    label={`${sampleBlastPlan.economic_metrics?.total_charge}kg total`}
                    variant="outlined"
                    size="small"
                  />
                </Stack>
                <Typography variant="body2" color="text.secondary">
                  Predicted P80: {sampleBlastPlan.predicted_fragmentation?.p80}mm
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Powder Factor: {sampleBlastPlan.economic_metrics?.powder_factor} kg/t
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Estimated Cost: ${sampleBlastPlan.economic_metrics?.estimated_cost}
                </Typography>
              </CardContent>
              <CardActions>
                <Button size="small">View Details</Button>
                <Button 
                  size="small" 
                  startIcon={<TuneIcon />}
                  onClick={() => navigate(`/blast-plans/${sampleBlastPlan.id}/optimize`)}
                >
                  Optimize
                </Button>
                <Button size="small">Export</Button>
              </CardActions>
            </Card>

            {/* Selected Hole Details */}
            {selectedHole && (
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Selected Hole: {selectedHole.hole_id}
                  </Typography>
                  <Stack spacing={1}>
                    <Typography variant="body2">
                      <strong>Position:</strong> ({selectedHole.coordinates.x}, {selectedHole.coordinates.y})
                    </Typography>
                    <Typography variant="body2">
                      <strong>Depth:</strong> {selectedHole.depth}m
                    </Typography>
                    <Typography variant="body2">
                      <strong>Charge:</strong> {selectedHole.charge_kg}kg
                    </Typography>
                    <Typography variant="body2">
                      <strong>Delay:</strong> {selectedHole.delay_ms}ms
                    </Typography>
                    <Typography variant="body2">
                      <strong>Explosive:</strong> {selectedHole.explosive_type}
                    </Typography>
                  </Stack>
                </CardContent>
              </Card>
            )}

            <Paper sx={{ p: 3 }}>
              <Typography variant="body1" color="text.secondary">
                This is a demonstration of the interactive blast plan visualization.
                Click on holes in the map to see details, use the measurement tool,
                and try different color schemes.
              </Typography>
            </Paper>
          </Stack>
        </Grid>

        {/* Interactive Map */}
        {showMap && (
          <Grid item xs={12} md={8}>
            <Paper sx={{ height: 600, overflow: 'hidden' }}>
              <BlastPlanMap
                blastPlan={sampleBlastPlan}
                receptors={sampleReceptors}
                onHoleSelect={handleHoleSelect}
                onHoleEdit={handleHoleEdit}
                onMeasurement={handleMeasurement}
                editable={true}
                showControls={true}
              />
            </Paper>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};