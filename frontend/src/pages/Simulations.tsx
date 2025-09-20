/**
 * Simulations page - Advanced simulation management interface
 */

import React from 'react';
import { Box, Typography, Container } from '@mui/material';
import { SimulationInterface } from '../components/Simulation';

export const Simulations: React.FC = () => {
  return (
    <Container maxWidth="xl">
      <Box py={3}>
        <Typography variant="h4" component="h1" gutterBottom>
          Advanced Simulations
        </Typography>
        <Typography variant="body1" color="text.secondary" paragraph>
          Run high-fidelity simulations using blastFoam CFD and YADE DEM for detailed blast analysis and fragmentation prediction.
        </Typography>
        
        <SimulationInterface />
      </Box>
    </Container>
  );
};