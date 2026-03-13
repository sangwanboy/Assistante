import type { StreamEvent } from '../types';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private messageQueue: { content: string; model: string; temperature: number; systemPrompt?: string; isGroup?: boolean }[] = [];
  private reconnectAttempts = 0;
  private maxReconnects = 10;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private currentConversationId: string | null = null;
  private _manualDisconnect = false;

  private onEvent: (event: StreamEvent) => void;
  private onOpen: () => void;
  private onClose: () => void;

  constructor(handlers: {
    onEvent: (event: StreamEvent) => void;
    onOpen?: () => void;
    onClose?: () => void;
  }) {
    this.onEvent = handlers.onEvent;
    this.onOpen = handlers.onOpen || (() => { });
    this.onClose = handlers.onClose || (() => { });
  }

  connect(conversationId: string) {
    // Reuse healthy/in-flight connection for same conversation to avoid churn.
    if (
      this.currentConversationId === conversationId &&
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this._manualDisconnect = false;
    this.reconnectAttempts = 0;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.currentConversationId = conversationId;
    this._doConnect();
  }

  private _doConnect() {
    // If already connected/connecting for current conversation, don't recreate socket.
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    // Clean up any existing socket without triggering reconnect
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.close();
      this.ws = null;
    }

    const conversationId = this.currentConversationId;
    if (!conversationId || this._manualDisconnect) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const hostname = window.location.hostname;
    // On Windows, localhost may resolve to ::1 while backend is bound on 127.0.0.1 only.
    const host = hostname === 'localhost' || hostname === '::1' ? '127.0.0.1' : hostname;
    const wsUrl = `${protocol}//${host}:8322/ws/chat/${conversationId}`;
    console.log('[WS Chat] Connecting to:', wsUrl, `(attempt ${this.reconnectAttempts + 1}/${this.maxReconnects})`);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('[WS Chat] Connected');
      this.reconnectAttempts = 0;
      this.onOpen();

      // Keep connection warm and detect dead sockets earlier.
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer);
      }
      this.heartbeatTimer = setInterval(() => {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
        try {
          this.ws.send(JSON.stringify({ type: 'ping' }));
        } catch {
          // onclose will handle recovery
        }
      }, 25000);

      // Flush any queued messages
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift();
        if (msg) {
          this.send(msg.content, msg.model, msg.temperature, msg.systemPrompt, msg.isGroup);
        }
      }
    };

    this.ws.onclose = (ev) => {
      console.log('[WS Chat] Closed. code:', ev.code, 'reason:', ev.reason);
      if (this.heartbeatTimer) {
        clearInterval(this.heartbeatTimer);
        this.heartbeatTimer = null;
      }
      this.onClose();

      // Reconnect unless manually disconnected or max retries exceeded.
      // Don't check ev.wasClean — server restarts often send wasClean=true with code 1001/1006.
      if (!this._manualDisconnect && this.currentConversationId && this.reconnectAttempts < this.maxReconnects) {
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000); // 1s, 2s, 4s … capped at 30s
        this.reconnectAttempts++;
        console.log(`[WS Chat] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnects})`);
        this.reconnectTimer = setTimeout(() => this._doConnect(), delay);
      }
    };

    this.ws.onmessage = (evt) => {
      try {
        const event: StreamEvent = JSON.parse(evt.data);
        this.onEvent(event);
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onerror = (ev) => {
      // Log only — onclose will fire next and handle reconnect
      console.error('[WS Chat] Error event:', ev);
    };
  }

  send(content: string, model: string, temperature: number = 0.7, systemPrompt?: string, isGroup?: boolean) {
    if (!this.ws || this.ws.readyState === WebSocket.CLOSING || this.ws.readyState === WebSocket.CLOSED) {
      // Queue and trigger reconnect
      this.messageQueue.push({ content, model, temperature, systemPrompt, isGroup });
      if (this.currentConversationId && !this.reconnectTimer) {
        this._doConnect();
      }
      return;
    }
    if (this.ws.readyState === WebSocket.CONNECTING) {
      // Queue — will flush on onopen
      this.messageQueue.push({ content, model, temperature, systemPrompt, isGroup });
      return;
    }
    this.ws.send(
      JSON.stringify({
        type: 'message',
        content,
        model,
        temperature,
        system_prompt: systemPrompt,
        is_group: isGroup,
      })
    );
  }

  disconnect() {
    this._manualDisconnect = true;
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.currentConversationId = null;
    this.reconnectAttempts = 0;
    if (this.ws) {
      this.ws.onopen = null;
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
