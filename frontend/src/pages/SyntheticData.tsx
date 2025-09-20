import React from 'react';
import { Container } from '@mui/material';
import { SyntheticDataInterface } from '../components/Synthetic';

const SyntheticData: React.FC = () => {
  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <SyntheticDataInterface />
    </Container>
  );
};

export default SyntheticData;