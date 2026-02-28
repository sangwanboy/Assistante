import type { StreamEvent } from '../types';

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private messageQueue: { content: string; model: string; temperature: number; systemPrompt?: string; isGroup?: boolean }[] = [];

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
    this.disconnect();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.ws = new WebSocket(`${protocol}//${host}/ws/chat/${conversationId}`);

    this.ws.onopen = () => {
      this.onOpen();
      // Flush any queued messages
      while (this.messageQueue.length > 0) {
        const msg = this.messageQueue.shift();
        if (msg) {
          this.send(msg.content, msg.model, msg.temperature, msg.systemPrompt, msg.isGroup);
        }
      }
    };
    this.ws.onclose = () => this.onClose();

    this.ws.onmessage = (evt) => {
      try {
        const event: StreamEvent = JSON.parse(evt.data);
        this.onEvent(event);
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onerror = () => {
      this.onEvent({ type: 'error', error: 'WebSocket connection failed' });
    };
  }

  send(content: string, model: string, temperature: number = 0.7, systemPrompt?: string, isGroup?: boolean) {
    if (!this.ws) {
      this.onEvent({ type: 'error', error: 'WebSocket not initialized' });
      return;
    }
    if (this.ws.readyState === WebSocket.CONNECTING) {
      // Queue the message to be sent once the connection opens
      this.messageQueue.push({ content, model, temperature, systemPrompt, isGroup });
      return;
    }
    if (this.ws.readyState !== WebSocket.OPEN) {
      this.onEvent({ type: 'error', error: 'WebSocket not connected' });
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
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
