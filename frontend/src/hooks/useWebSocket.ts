import { useEffect, useRef, useState } from 'react'
import type { ActivityEvent } from '../types'

export interface UseWebSocketResult {
  events: ActivityEvent[]
  status: 'connecting' | 'open' | 'closed' | 'error'
  lastMessage: { type: string; investigation_id?: string; events?: ActivityEvent[] } | null
}

export function useWebSocket(investigationId: string | null): UseWebSocketResult {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [status, setStatus] = useState<'connecting' | 'open' | 'closed' | 'error'>('closed')
  const [lastMessage, setLastMessage] = useState<UseWebSocketResult['lastMessage']>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const seenRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!investigationId) {
      setStatus('closed')
      setEvents([])
      return
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}/ws/investigation/${investigationId}`
    setStatus('connecting')
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => setStatus('open')
    ws.onclose = () => setStatus('closed')
    ws.onerror = () => setStatus('error')

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as { type?: string; investigation_id?: string; events?: ActivityEvent[] }
        setLastMessage(data)
        if (data.type === 'activity' && Array.isArray(data.events)) {
          setEvents((prev) => {
            const next = [...prev]
            for (const ev of data.events as ActivityEvent[]) {
              const key = `${ev.agent}-${ev.step}-${ev.timestamp}`
              if (seenRef.current.has(key)) continue
              seenRef.current.add(key)
              next.push(ev)
            }
            return next.slice(-200)
          })
        }
      } catch {
        // ignore parse errors
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [investigationId])

  return { events, status, lastMessage }
}
