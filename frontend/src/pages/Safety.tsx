import React from 'react';
import {
  Box,
  Typography,
  Paper,
} from '@mui/material';

export const Safety: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Safety Validation
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="body1" color="text.secondary">
          Safety validation results will be displayed here once blast plans are created.
        </Typography>
      </Paper>
    </Box>
  );
};