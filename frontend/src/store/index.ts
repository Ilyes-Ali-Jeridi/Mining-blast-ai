import { configureStore } from '@reduxjs/toolkit';

// Simple store configuration for now
export const store = configureStore({
  reducer: {
    // Add reducers here as needed
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;