export { default as OptimizationInterface } from './OptimizationInterface';
export { default as OptimizationConfig } from './OptimizationConfig';
export { default as OptimizationProgress } from './OptimizationProgress';
export { default as OptimizationResults } from './OptimizationResults';

// Re-export types with different names to avoid conflicts
export type {
  OptimizationSession,
  OptimizationResult,
  OptimizationHistory,
  WebSocketMessage
} from '../../types';