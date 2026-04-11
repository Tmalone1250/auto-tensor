import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { Terminal } from '@xterm/xterm';

// Derive ws:// or wss:// from the VITE_API_URL env var
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TERMINAL_SECRET = import.meta.env.VITE_TERMINAL_SECRET || '';

function buildWsUrl(sessionId: string): string {
  const wsBase = API_BASE.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://');
  return `${wsBase}/ws/terminal?token=${encodeURIComponent(TERMINAL_SECRET)}&session_id=${encodeURIComponent(sessionId)}`;
}

export type ConnState = 'connecting' | 'connected' | 'disconnected' | 'auth_error';

interface TerminalContextType {
  connState: ConnState;
  attachTerminal: (container: HTMLDivElement, term: Terminal) => () => void;
  sendData: (data: string | Uint8Array) => void;
  sendResize: (cols: number, rows: number) => void;
  clearBuffer: () => void;
  reconnect: (sessionId?: string) => void;
}

const TerminalContext = createContext<TerminalContextType | null>(null);

export const useTerminal = () => {
  const context = useContext(TerminalContext);
  if (!context) {
    throw new Error('useTerminal must be used within a TerminalProvider');
  }
  return context;
};

export const TerminalProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [connState, setConnState] = useState<ConnState>('connecting');
  const [currentSessionId, setCurrentSessionId] = useState('trevor-main');
  
  const wsRef = useRef<WebSocket | null>(null);
  const activeTermRef = useRef<Terminal | null>(null);

  const connect = useCallback((sessionId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    setConnState('connecting');
    const ws = new WebSocket(buildWsUrl(sessionId));
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;

    ws.onopen = () => {
      setConnState('connected');
      if (activeTermRef.current) {
        ws.send(JSON.stringify({ 
          type: 'resize', 
          cols: activeTermRef.current.cols, 
          rows: activeTermRef.current.rows 
        }));
      }
    };

    ws.onmessage = (event) => {
      if (!activeTermRef.current) return;
      
      if (event.data instanceof ArrayBuffer) {
        const decoder = new TextDecoder();
        activeTermRef.current.write(decoder.decode(event.data));
      } else if (typeof event.data === 'string') {
        activeTermRef.current.write(event.data);
      }
    };

    ws.onclose = (event) => {
      if (event.code === 4401) {
        setConnState('auth_error');
      } else {
        setConnState('disconnected');
      }
    };

    ws.onerror = () => {
      setConnState('disconnected');
    };
  }, []);

  useEffect(() => {
    connect(currentSessionId);
    return () => {
      wsRef.current?.close();
    };
  }, [connect, currentSessionId]);

  const attachTerminal = useCallback((container: HTMLDivElement, term: Terminal) => {
    activeTermRef.current = term;
    term.open(container);
    
    // If already connected, sync size
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ 
        type: 'resize', 
        cols: term.cols, 
        rows: term.rows 
      }));
    }

    const dataDisposable = term.onData((data) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(new TextEncoder().encode(data));
      }
    });

    return () => {
      dataDisposable.dispose();
      activeTermRef.current = null;
    };
  }, []);

  const sendData = useCallback((data: string | Uint8Array) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      if (typeof data === 'string') {
        wsRef.current.send(new TextEncoder().encode(data));
      } else {
        wsRef.current.send(data);
      }
    }
  }, []);

  const sendResize = useCallback((cols: number, rows: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'resize', cols, rows }));
    }
  }, []);

  const clearBuffer = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'clear_buffer' }));
    }
    if (activeTermRef.current) {
      activeTermRef.current.clear();
    }
  }, []);

  const reconnect = useCallback((sessionId?: string) => {
    if (sessionId) setCurrentSessionId(sessionId);
    connect(sessionId || currentSessionId);
  }, [connect, currentSessionId]);

  return (
    <TerminalContext.Provider value={{ 
      connState, 
      attachTerminal, 
      sendData, 
      sendResize, 
      clearBuffer,
      reconnect 
    }}>
      {children}
    </TerminalContext.Provider>
  );
};
