import React from 'react';
import { Box, Typography } from '@mui/material';
import { BlastPlan, DrillHole } from '../../types';

interface BlastPlanMapProps {
  blastPlan?: BlastPlan;
  onHoleSelect?: (hole: DrillHole) => void;
  onHoleEdit?: (hole: DrillHole) => void;
  onMeasurement?: (distance: number, area: number) => void;
  editable?: boolean;
  showControls?: boolean;
}

export const BlastPlanMap: React.FC<BlastPlanMapProps> = ({
  blastPlan,
  onHoleSelect,
  onHoleEdit,
  onMeasurement,
  editable = false,
  showControls = true,
}) => {
  return (
    <Box 
      sx={{ 
        height: '100%', 
        width: '100%', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: '#f5f5f5',
        border: '1px solid #ddd'
      }}
    >
      <Typography variant="h6" color="text.secondary">
        Interactive Map Loading...
        {blastPlan && ` (${blastPlan.holes.length} holes)`}
      </Typography>
    </Box>
  );
};