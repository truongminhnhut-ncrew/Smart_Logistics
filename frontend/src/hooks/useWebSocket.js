/**
 * hooks/useWebSocket.js — WebSocket with typed messages + auto-reconnect
 */

import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://127.0.0.1:8000/ws'

export const useWebSocket = () => {
  const ws = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const listeners = useRef(new Map()) // type -> Set of callbacks
  const reconnectTimer = useRef(null)
  const mountedRef = useRef(true)

  const connect = useCallback(() => {
    if (!mountedRef.current) return
    
    // Tránh tạo nhiều connection nếu đang kết nối hoặc đã mở
    if (ws.current && (ws.current.readyState === WebSocket.CONNECTING || ws.current.readyState === WebSocket.OPEN)) return;

    try {
      console.log('[WS] Connecting to', WS_URL)
      ws.current = new WebSocket(WS_URL)

      ws.current.onopen = () => {
        if (!mountedRef.current) return
        console.log('[WS] Connected to', WS_URL)
        setIsConnected(true)
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current)
          reconnectTimer.current = null
        }
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          const type = data.type || 'unknown'

          // Notify all listeners for this type
          const typeListeners = listeners.current.get(type);
          if (typeListeners) {
            typeListeners.forEach(cb => cb(data))
          }
          // Notify wildcard listeners
          const wildcardListeners = listeners.current.get('*');
          if (wildcardListeners) {
            wildcardListeners.forEach(cb => cb(data))
          }
        } catch (e) {
          // Tránh log spam nếu nhận dữ liệu không phải JSON
        }
      }

      ws.current.onerror = (err) => {
        console.warn('[WS] Error — will reconnect', err)
      }

      ws.current.onclose = () => {
        if (!mountedRef.current) return
        if (ws.current?.readyState === WebSocket.CLOSED) setIsConnected(false);
        console.log('[WS] Disconnected — reconnecting in 3s...')
        reconnectTimer.current = setTimeout(connect, 3000)
      }
    } catch (e) {
      console.error('[WS] Connect error:', e)
      reconnectTimer.current = setTimeout(connect, 3000)
    }
  }, [])

  useEffect(() => {
    mountedRef.current = true
    connect()
    return () => {
      mountedRef.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (ws.current) ws.current.close()
    }
  }, [connect])

  const on = useCallback((type, callback) => {
    if (!listeners.current.has(type)) {
      listeners.current.set(type, new Set())
    }
    listeners.current.get(type).add(callback)
    return () => {
      if (listeners.current.has(type)) {
        listeners.current.get(type).delete(callback)
      }
    }
  }, [])

  const subscribe = useCallback((callback) => on('*', callback), [on])

  return { isConnected, on, subscribe }
}
