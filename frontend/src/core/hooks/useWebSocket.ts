import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthStore } from "@/core/stores/auth";

interface WebSocketMessage {
  type: "notification" | "system" | "pong" | "connected";
  event?: string;
  data?: unknown;
  timestamp?: number;
  target_role?: string;
}

interface UseWebSocketOptions {
  onNotification?: (event: string, data: unknown) => void;
  onSystemMessage?: (event: string, data: unknown) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const token = useAuthStore((s) => s.token);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const maxDelay = 30_000;
  const baseDelay = 1000;

  const connect = useCallback(() => {
    if (!token || wsRef.current?.readyState === WebSocket.OPEN) return;

    setIsReconnecting(reconnectAttempts.current > 0);

    const wsUrl = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/notifications/ws?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsReconnecting(false);
      reconnectAttempts.current = 0;
      options.onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        setLastMessage(message);

        if (message.type === "notification") {
          options.onNotification?.(message.event ?? "unknown", message.data);
        } else if (message.type === "system") {
          options.onSystemMessage?.(message.event ?? "unknown", message.data);
        }
      } catch {
        /* ignore malformed messages */
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      options.onDisconnect?.();

      const delay = Math.min(baseDelay * Math.pow(2, reconnectAttempts.current), maxDelay);
      reconnectAttempts.current++;
      setIsReconnecting(true);
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [token, options]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    reconnectAttempts.current = 0;
    setIsReconnecting(false);
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const ping = useCallback(() => {
    send({ type: "ping" });
  }, [send]);

  useEffect(() => {
    if (token) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [token, connect, disconnect]);

  useEffect(() => {
    if (!isConnected) return;
    const interval = setInterval(ping, 30000);
    return () => clearInterval(interval);
  }, [isConnected, ping]);

  return { isConnected, isReconnecting, lastMessage, send, ping, connect, disconnect };
}
