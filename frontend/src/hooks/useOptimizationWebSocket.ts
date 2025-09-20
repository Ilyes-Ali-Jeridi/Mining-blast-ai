import { useEffect, useRef, useState, useCallback } from 'react';
import { OptimizationProgress, WebSocketMessage } from '../types';

interface UseOptimizationWebSocketProps {
  optimizationId: string | null;
  onProgress?: (progress: OptimizationProgress) => void;
  onCompleted?: (result: any) => void;
  onFailed?: (error: string) => void;
  onCancelled?: () => void;
}

interface WebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: WebSocketMessage | null;
}

export const useOptimizationWebSocket = ({
  optimizationId,
  onProgress,
  onCompleted,
  onFailed,
  onCancelled
}: UseOptimizationWebSocketProps) => {
  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!optimizationId || wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setState(prev => ({ ...prev, isConnecting: true, error: null }));

    try {
      const wsUrl = `${import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000'}/api/v1/ws/optimization/${optimizationId}`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected for optimization ${optimizationId}`);
        setState(prev => ({ 
          ...prev, 
          isConnected: true, 
          isConnecting: false, 
          error: null 
        }));
        reconnectAttempts.current = 0;

        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          setState(prev => ({ ...prev, lastMessage: message }));

          switch (message.type) {
            case 'optimization_progress':
              if (onProgress && message.optimization_id === optimizationId) {
                onProgress({
                  iteration: message.iterations || 0,
                  objective_value: message.current_objective || 0,
                  best_objective: message.best_objective || 0,
                  status: message.status || 'running',
                  message: message.message,
                  algorithm: message.algorithm,
                  progress_percentage: message.progress_percentage,
                  elapsed_time: message.elapsed_time,
                  function_evaluations: message.function_evaluations
                });
              }
              break;

            case 'optimization_completed':
              if (onCompleted && message.optimization_id === optimizationId) {
                onCompleted(message.result);
              }
              break;

            case 'optimization_failed':
              if (onFailed && message.optimization_id === optimizationId) {
                onFailed(message.error || 'Optimization failed');
              }
              break;

            case 'optimization_cancelled':
              if (onCancelled && message.optimization_id === optimizationId) {
                onCancelled();
              }
              break;

            case 'pong':
              // Handle ping/pong for connection health
              break;

            case 'error':
              console.error('WebSocket error message:', message.message);
              setState(prev => ({ ...prev, error: message.message }));
              break;

            default:
              console.log('Unknown WebSocket message type:', message.type);
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setState(prev => ({ 
          ...prev, 
          error: 'WebSocket connection error',
          isConnecting: false 
        }));
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setState(prev => ({ 
          ...prev, 
          isConnected: false, 
          isConnecting: false 
        }));

        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Attempt to reconnect if not a normal closure
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          reconnectAttempts.current++;
          
          console.log(`Attempting to reconnect in ${delay}ms (attempt ${reconnectAttempts.current})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setState(prev => ({ 
        ...prev, 
        error: 'Failed to create WebSocket connection',
        isConnecting: false 
      }));
    }
  }, [optimizationId, onProgress, onCompleted, onFailed, onCancelled]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setState({
      isConnected: false,
      isConnecting: false,
      error: null,
      lastMessage: null
    });
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    }
    return false;
  }, []);

  const cancelOptimization = useCallback(() => {
    return sendMessage({ type: 'cancel_optimization' });
  }, [sendMessage]);

  const requestStatus = useCallback(() => {
    return sendMessage({ type: 'get_status' });
  }, [sendMessage]);

  // Connect when optimization ID is provided
  useEffect(() => {
    if (optimizationId) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [optimizationId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    cancelOptimization,
    requestStatus
  };
};