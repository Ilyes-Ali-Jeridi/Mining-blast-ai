import React from 'react';
import {
  Box,
  Typography,
  Paper,
} from '@mui/material';

export const Reports: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Reports
      </Typography>

      <Paper sx={{ p: 3 }}>
        <Typography variant="body1" color="text.secondary">
          Generated reports and exports will be available here.
        </Typography>
      </Paper>
    </Box>
  );
};