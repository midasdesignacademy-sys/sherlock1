import { useMemo, useState } from 'react'
import { FileText, Cpu, GitBranch, ShieldCheck, Brain, Link2, Clock, Sparkles, Network, FileStack, Shield } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import type { ActivityEvent } from '../types'

const AGENT_ORDER = [
  'ingest_documents',
  'classify_documents',
  'extract_entities',
  'cryptanalysis_hunter',
  'semantic_linker',
  'timeline',
  'pattern_recognition',
  'build_knowledge_graph',
  'synthesis',
  'odos_guardian',
] as const

const AGENT_LABELS: Record<string, string> = {
  ingest_documents: 'Ingest',
  classify_documents: 'Classify',
  extract_entities: 'Entities',
  cryptanalysis_hunter: 'Crypto',
  semantic_linker: 'Semantic',
  timeline: 'Timeline',
  pattern_recognition: 'Patterns',
  build_knowledge_graph: 'KG',
  synthesis: 'Synthesis',
  odos_guardian: 'Guardian',
}

const AGENT_ICONS: Record<string, React.ReactNode> = {
  ingest_documents: <FileText className="w-4 h-4" />,
  classify_documents: <Cpu className="w-4 h-4" />,
  extract_entities: <Brain className="w-4 h-4" />,
  cryptanalysis_hunter: <Shield className="w-4 h-4" />,
  semantic_linker: <Link2 className="w-4 h-4" />,
  timeline: <Clock className="w-4 h-4" />,
  pattern_recognition: <Sparkles className="w-4 h-4" />,
  build_knowledge_graph: <Network className="w-4 h-4" />,
  synthesis: <FileStack className="w-4 h-4" />,
  odos_guardian: <ShieldCheck className="w-4 h-4" />,
}

type NodeStatus = 'idle' | 'active' | 'done' | 'error'

function deriveAgentStatus(events: ActivityEvent[], agent: string): NodeStatus {
  const agentEvents = events.filter((e) => e.agent === agent)
  const last = agentEvents[agentEvents.length - 1]
  if (!last) return 'idle'
  if (last.step === 'error') return 'error'
  if (last.step === 'end') return 'done'
  if (last.step === 'start') return 'active'
  return 'idle'
}

export function PipelineMonitor({ investigationId }: { investigationId: string }) {
  const { events, status } = useWebSocket(investigationId)
  const [drawerAgent, setDrawerAgent] = useState<string | null>(null)

  const agentStatus = useMemo(() => {
    const m: Record<string, NodeStatus> = {}
    for (const a of AGENT_ORDER) m[a] = deriveAgentStatus(events, a)
    return m
  }, [events])

  const agentEvents = useMemo(() => {
    if (!drawerAgent) return []
    return events.filter((e) => e.agent === drawerAgent)
  }, [events, drawerAgent])

  if (!investigationId) {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-gray-500">
        No investigation selected
      </div>
    )
  }

  if (status === 'connecting') {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-gray-500">
        Connecting…
      </div>
    )
  }

  return (
    <div className="rounded border border-gray-200 bg-white p-4">
      <div className="flex flex-wrap gap-2 items-center">
        {AGENT_ORDER.map((agent) => {
          const nodeStatus = agentStatus[agent]
          const isActive = nodeStatus === 'active'
          const isDone = nodeStatus === 'done'
          const isError = nodeStatus === 'error'
          const isIdle = nodeStatus === 'idle'
          const base =
            'flex items-center gap-1.5 px-3 py-2 rounded-lg border cursor-pointer transition-all ' +
            (isError
              ? 'bg-red-100 border-red-300 text-red-800'
              : isActive
                ? 'bg-green-100 border-green-400 text-green-900 animate-pulse'
                : isDone
                  ? 'bg-green-50 border-green-200 text-green-800'
                  : isIdle
                    ? 'bg-gray-50 border-gray-200 text-gray-500 opacity-60'
                    : 'bg-gray-50 border-gray-200')
          return (
            <button
              key={agent}
              type="button"
              className={base}
              onClick={() => setDrawerAgent(drawerAgent === agent ? null : agent)}
              title={AGENT_LABELS[agent] ?? agent}
            >
              {AGENT_ICONS[agent] ?? <GitBranch className="w-4 h-4" />}
              <span className="text-sm font-medium">{AGENT_LABELS[agent] ?? agent}</span>
            </button>
          )
        })}
      </div>

      {drawerAgent && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-gray-900">Logs: {AGENT_LABELS[drawerAgent] ?? drawerAgent}</h3>
            <button
              type="button"
              className="text-gray-500 hover:text-gray-700"
              onClick={() => setDrawerAgent(null)}
              aria-label="Fechar"
            >
              ✕
            </button>
          </div>
          <ul className="max-h-48 overflow-y-auto space-y-1 text-sm">
            {agentEvents.length === 0 && <li className="text-gray-500">Nenhum evento ainda</li>}
            {agentEvents.map((ev, i) => (
              <li key={i} className="text-gray-700">
                <span className="text-gray-500">{ev.timestamp}</span> {ev.step}
                {ev.payload && Object.keys(ev.payload).length > 0 && (
                  <span className="ml-2 text-gray-600">{JSON.stringify(ev.payload)}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
