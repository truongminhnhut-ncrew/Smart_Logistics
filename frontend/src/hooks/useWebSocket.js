/**
 * hooks/useWebSocket.js — WebSocket custom hook
 *
 * Manages connection to ws://localhost:8000/ws
 * Broadcasts real-time GPS updates to components
 */

import { useEffect, useRef, useState } from 'react'

export const useWebSocket = (url = 'ws://localhost:8000/ws') => {
  const ws = useRef(null)
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const listeners = useRef(new Set())

  useEffect(() => {
    // Connect to WebSocket
    ws.current = new WebSocket(url)

    ws.current.onopen = () => {
      console.log('[WebSocket] Connected')
      setIsConnected(true)
    }

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setLastMessage(data)
        // Notify all listeners
        listeners.current.forEach(listener => listener(data))
      } catch (e) {
        console.error('[WebSocket] Parse error:', e)
      }
    }

    ws.current.onerror = (error) => {
      console.error('[WebSocket] Error:', error)
    }

    ws.current.onclose = () => {
      console.log('[WebSocket] Disconnected')
      setIsConnected(false)
    }

    return () => {
      if (ws.current) ws.current.close()
    }
  }, [url])

  const subscribe = (callback) => {
    listeners.current.add(callback)
    return () => listeners.current.delete(callback)
  }

  return {
    isConnected,
    lastMessage,
    subscribe,
  }
}
