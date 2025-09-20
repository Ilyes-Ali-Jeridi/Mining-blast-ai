/**
 * Custom hook for WebSocket connection to simulation progress updates
 */

import { useState, useEffect, useRef, useCallback } from 'react';

export interface SimulationWebSocketMessage {
  type: string;
  simulation_job_id?: string;
  timestamp: string;
  [key: string]: any;
}

export interface SimulationProgressData {
  progress?: number;
  status?: string;
  message?: string;
  current_step?: string;
  total_steps?: number;
  elapsed_time?: number;
  estimated_remaining?: number;
}

export interface SimulationWebSocketState {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  lastMessage: SimulationWebSocketMessage | null;
  connectionId: string | null;
}

export interface UseSimulationWebSocketReturn extends SimulationWebSocketState {
  connect: (simulationJobId: string) => void;
  disconnect: () => void;
  sendMessage: (message: any) => void;
  cancelSimulation: () => void;
  requestStatus: () => void;
}

const WEBSOCKET_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';
const RECONNECT_INTERVAL = 5000; // 5 seconds
const MAX_RECONNECT_ATTEMPTS = 10;
const PING_INTERVAL = 30000; // 30 seconds

export function useSimulationWebSocket(): UseSimulationWebSocketReturn {
  const [state, setState] = useState<SimulationWebSocketState>({
    isConnected: false,
    isConnecting: false,
    error: null,
    lastMessage: null,
    connectionId: null,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const simulationJobIdRef = useRef<string | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isManualDisconnectRef = useRef(false);

  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  const startPingInterval = useCallback(() => {
    clearTimeouts();
    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          type: 'ping',
          timestamp: new Date().toISOString()
        }));
      }
    }, PING_INTERVAL);
  }, [clearTimeouts]);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: SimulationWebSocketMessage = JSON.parse(event.data);
      
      setState(prev => ({
        ...prev,
        lastMessage: message,
        error: null
      }));

      // Handle specific message types
      switch (message.type) {
        case 'simulation_connected':
          setState(prev => ({
            ...prev,
            connectionId: message.connection_id || null
          }));
          break;
        
        case 'simulation_started':
          console.log('Simulation started:', message.simulation_job_id);
          break;
        
        case 'simulation_progress':
          console.log('Simulation progress:', message);
          break;
        
        case 'simulation_completed':
          console.log('Simulation completed:', message.simulation_job_id);
          break;
        
        case 'simulation_failed':
          console.error('Simulation failed:', message.error);
          break;
        
        case 'simulation_cancelled':
          console.log('Simulation cancelled:', message.simulation_job_id);
          break;
        
        case 'error':
          setState(prev => ({
            ...prev,
            error: message.message || 'Unknown error'
          }));
          break;
        
        case 'pong':
          // Handle pong response
          break;
        
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to parse message'
      }));
    }
  }, []);

  const handleOpen = useCallback(() => {
    console.log('Simulation WebSocket connected');
    setState(prev => ({
      ...prev,
      isConnected: true,
      isConnecting: false,
      error: null
    }));
    
    reconnectAttemptsRef.current = 0;
    startPingInterval();
  }, [startPingInterval]);

  const handleClose = useCallback((event: CloseEvent) => {
    console.log('Simulation WebSocket disconnected:', event.code, event.reason);
    
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      connectionId: null
    }));
    
    clearTimeouts();

    // Attempt to reconnect if not manually disconnected
    if (!isManualDisconnectRef.current && 
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS &&
        simulationJobIdRef.current) {
      
      reconnectAttemptsRef.current++;
      
      setState(prev => ({
        ...prev,
        error: `Connection lost. Reconnecting... (${reconnectAttemptsRef.current}/${MAX_RECONNECT_ATTEMPTS})`
      }));
      
      reconnectTimeoutRef.current = setTimeout(() => {
        if (simulationJobIdRef.current) {
          connectToSimulation(simulationJobIdRef.current);
        }
      }, RECONNECT_INTERVAL);
    } else if (reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
      setState(prev => ({
        ...prev,
        error: 'Failed to reconnect after maximum attempts'
      }));
    }
  }, [clearTimeouts]);

  const handleError = useCallback((event: Event) => {
    console.error('Simulation WebSocket error:', event);
    setState(prev => ({
      ...prev,
      error: 'WebSocket connection error',
      isConnecting: false
    }));
  }, []);

  const connectToSimulation = useCallback((simulationJobId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    setState(prev => ({
      ...prev,
      isConnecting: true,
      error: null
    }));

    simulationJobIdRef.current = simulationJobId;
    isManualDisconnectRef.current = false;

    try {
      const wsUrl = `${WEBSOCKET_URL}/ws/simulation/${simulationJobId}`;
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = handleOpen;
      wsRef.current.onmessage = handleMessage;
      wsRef.current.onclose = handleClose;
      wsRef.current.onerror = handleError;
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setState(prev => ({
        ...prev,
        error: 'Failed to create WebSocket connection',
        isConnecting: false
      }));
    }
  }, [handleOpen, handleMessage, handleClose, handleError]);

  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;
    simulationJobIdRef.current = null;
    clearTimeouts();
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }
    
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      error: null,
      connectionId: null,
      lastMessage: null
    }));
  }, [clearTimeouts]);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        ...message,
        timestamp: new Date().toISOString()
      }));
    } else {
      console.warn('WebSocket is not connected');
      setState(prev => ({
        ...prev,
        error: 'WebSocket is not connected'
      }));
    }
  }, []);

  const cancelSimulation = useCallback(() => {
    sendMessage({
      type: 'cancel_simulation',
      simulation_job_id: simulationJobIdRef.current
    });
  }, [sendMessage]);

  const requestStatus = useCallback(() => {
    sendMessage({
      type: 'get_status',
      simulation_job_id: simulationJobIdRef.current
    });
  }, [sendMessage]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    ...state,
    connect: connectToSimulation,
    disconnect,
    sendMessage,
    cancelSimulation,
    requestStatus,
  };
}

/**
 * Hook for extracting simulation progress data from WebSocket messages
 */
export function useSimulationProgress(
  webSocketState: SimulationWebSocketState
): SimulationProgressData | null {
  const [progressData, setProgressData] = useState<SimulationProgressData | null>(null);

  useEffect(() => {
    if (!webSocketState.lastMessage) return;

    const message = webSocketState.lastMessage;

    switch (message.type) {
      case 'simulation_started':
        setProgressData({
          progress: 0,
          status: 'running',
          message: 'Simulation started',
          current_step: 'Initializing',
        });
        break;

      case 'simulation_progress':
        setProgressData({
          progress: message.progress || 0,
          status: 'running',
          message: message.message || 'Running simulation',
          current_step: message.current_step,
          total_steps: message.total_steps,
          elapsed_time: message.elapsed_time,
          estimated_remaining: message.estimated_remaining,
        });
        break;

      case 'simulation_completed':
        setProgressData({
          progress: 100,
          status: 'completed',
          message: 'Simulation completed successfully',
        });
        break;

      case 'simulation_failed':
        setProgressData({
          progress: 0,
          status: 'failed',
          message: message.error || 'Simulation failed',
        });
        break;

      case 'simulation_cancelled':
        setProgressData({
          progress: 0,
          status: 'cancelled',
          message: 'Simulation cancelled',
        });
        break;

      case 'simulation_status':
        setProgressData({
          status: message.status,
          message: `Status: ${message.status}`,
        });
        break;
    }
  }, [webSocketState.lastMessage]);

  return progressData;
}