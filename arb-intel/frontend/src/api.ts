// API client for backend communication

import type { Opportunity, Stats, FilterState } from './types';

const API_BASE = '/api';

export async function fetchOpportunities(filters: FilterState): Promise<{
  count: number;
  opportunities: Opportunity[];
  disclaimer: string;
}> {
  const params = new URLSearchParams();
  if (filters.type !== 'all') params.append('type', filters.type);
  if (filters.minProfit > 0) params.append('min_profit', filters.minProfit.toString());
  if (filters.risk !== 'all') params.append('risk', filters.risk);
  if (filters.sport) params.append('sport', filters.sport);

  const response = await fetch(`${API_BASE}/opportunities?${params}`);
  if (!response.ok) throw new Error('Failed to fetch opportunities');
  return response.json();
}

export async function fetchStats(): Promise<Stats> {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
}

export async function triggerScan(): Promise<{
  success: boolean;
  markets_scanned: number;
  opportunities_found: number;
  scan_duration_ms: number;
  opportunities: Opportunity[];
}> {
  const response = await fetch(`${API_BASE}/scan`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to trigger scan');
  return response.json();
}

export async function fetchHealth(): Promise<{
  status: string;
  scanner_running: boolean;
  last_scan: string | null;
  markets_cached: number;
  opportunities_count: number;
}> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) throw new Error('Failed to fetch health');
  return response.json();
}

export interface Source {
  name: string;
  id: string;
  type: string;
  description: string;
  markets: number;
  status: string;
  url: string;
}

export async function fetchSources(): Promise<{
  sources: Source[];
  total_markets: number;
  active_sources: number;
}> {
  const response = await fetch(`${API_BASE}/sources`);
  if (!response.ok) throw new Error('Failed to fetch sources');
  return response.json();
}

// WebSocket connection manager
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private onMessageCallback: ((data: unknown) => void) | null = null;
  private onStatusChangeCallback: ((connected: boolean) => void) | null = null;
  private intentionalDisconnect = false;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    if (this.ws?.readyState === WebSocket.CONNECTING) return;

    this.intentionalDisconnect = false;

    // Connect directly to backend WebSocket
    const wsUrl = 'ws://localhost:8000/ws';

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.onStatusChangeCallback?.(true);
    };

    this.ws.onclose = () => {
      if (!this.intentionalDisconnect) {
        console.log('WebSocket disconnected');
        this.onStatusChangeCallback?.(false);
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // Only log if not intentional disconnect (React StrictMode causes this)
      if (!this.intentionalDisconnect) {
        console.log('WebSocket connection error - will retry');
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.onMessageCallback?.(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };
  }

  private scheduleReconnect() {
    if (this.intentionalDisconnect) return;
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('Max reconnect attempts reached');
      return;
    }

    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;

    this.reconnectTimer = window.setTimeout(() => {
      console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
      this.connect();
    }, delay);
  }

  disconnect() {
    this.intentionalDisconnect = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(message: unknown) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  onMessage(callback: (data: unknown) => void) {
    this.onMessageCallback = callback;
  }

  onStatusChange(callback: (connected: boolean) => void) {
    this.onStatusChangeCallback = callback;
  }
}

export const wsManager = new WebSocketManager();
