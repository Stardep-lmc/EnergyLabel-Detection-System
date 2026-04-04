import webSocket from '@ohos.net.webSocket';
import { BASE_URL } from './Api';

// WebSocket 客户端 — 接收检测结果实时推送
export class WebSocketClient {
  private ws: webSocket.WebSocket | null = null;
  private wsUrl: string = '';
  private onMessage: ((data: object) => void) | null = null;
  private onStatusChange: ((connected: boolean) => void) | null = null;
  private heartbeatTimer: number = -1;
  private reconnectTimer: number = -1;
  private isConnected: boolean = false;
  private shouldReconnect: boolean = true;
  private reconnectDelay: number = 3000;

  constructor() {
    // 将 http:// 转为 ws://
    let base = BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
    this.wsUrl = base + '/ws/detection';
  }

  setOnMessage(callback: (data: object) => void) {
    this.onMessage = callback;
  }

  setOnStatusChange(callback: (connected: boolean) => void) {
    this.onStatusChange = callback;
  }

  connect() {
    this.shouldReconnect = true;
    this.doConnect();
  }

  private doConnect() {
    try {
      this.ws = webSocket.createWebSocket();

      this.ws.on('open', () => {
        this.isConnected = true;
        if (this.onStatusChange) this.onStatusChange(true);
        this.startHeartbeat();
      });

      this.ws.on('message', (err: Error, data: string | ArrayBuffer) => {
        if (err) return;
        let msg = data as string;
        if (msg === 'pong') return; // 心跳回复
        try {
          let parsed = JSON.parse(msg);
          if (this.onMessage) this.onMessage(parsed);
        } catch (e) { /* ignore non-JSON */ }
      });

      this.ws.on('close', () => {
        this.isConnected = false;
        if (this.onStatusChange) this.onStatusChange(false);
        this.stopHeartbeat();
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      });

      this.ws.on('error', () => {
        this.isConnected = false;
        if (this.onStatusChange) this.onStatusChange(false);
        this.stopHeartbeat();
        if (this.shouldReconnect) {
          this.scheduleReconnect();
        }
      });

      this.ws.connect(this.wsUrl);
    } catch (e) {
      if (this.shouldReconnect) {
        this.scheduleReconnect();
      }
    }
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.isConnected) {
        try { this.ws.send('ping'); } catch (e) { /* ignore */ }
      }
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer !== -1) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = -1;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer !== -1) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = -1;
      this.doConnect();
    }, this.reconnectDelay);
  }

  disconnect() {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    if (this.reconnectTimer !== -1) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = -1;
    }
    if (this.ws) {
      try { this.ws.close(); } catch (e) { /* ignore */ }
      this.ws = null;
    }
    this.isConnected = false;
  }

  getConnected(): boolean {
    return this.isConnected;
  }
}