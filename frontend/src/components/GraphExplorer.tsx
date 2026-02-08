import { useMemo, useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import CytoscapeComponent from 'react-cytoscapejs'
import type { Core } from 'cytoscape'
import { fetchInvestigationGraph } from '../api/graph'
import type { GraphNode, GraphEdge } from '../types'

const LAYOUT = { name: 'cose', animate: false }

export function GraphExplorer({ investigationId }: { investigationId: string }) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['graph', investigationId],
    queryFn: () => fetchInvestigationGraph(investigationId),
    enabled: !!investigationId,
  })
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string; docId?: string; label?: string } | null>(null)
  const [filterEntityTypes, setFilterEntityTypes] = useState<Set<string>>(new Set())
  const [filterEdgeTypes, setFilterEdgeTypes] = useState<Set<string>>(new Set())

  const rawNodes = data?.elements?.nodes ?? []
  const rawEdges = data?.elements?.edges ?? []

  const entityTypes = useMemo(() => {
    const set = new Set<string>()
    rawNodes.forEach((n: GraphNode) => {
      const t = n.data.entity_type as string
      if (t) set.add(t)
    })
    return Array.from(set).sort()
  }, [rawNodes])

  const edgeTypes = useMemo(() => {
    const set = new Set<string>()
    rawEdges.forEach((e: GraphEdge) => {
      const t = e.data.relationship_type as string
      if (t) set.add(t)
    })
    return Array.from(set).sort()
  }, [rawEdges])

  const elements = useMemo(() => {
    const etFilter = filterEntityTypes.size > 0 ? filterEntityTypes : null
    const edgeFilter = filterEdgeTypes.size > 0 ? filterEdgeTypes : null
    const nodes = rawNodes
      .filter((n: GraphNode) => !etFilter || (n.data.entity_type && etFilter.has(n.data.entity_type as string)))
      .map((n: GraphNode) => ({ group: 'nodes' as const, data: n.data }))
    const allowedSources = new Set(nodes.map((n: { data: { id: string } }) => n.data.id))
    const edges = rawEdges
      .filter((e: GraphEdge) => {
        if (!allowedSources.has(e.data.source) || !allowedSources.has(e.data.target)) return false
        if (edgeFilter && e.data.relationship_type) return edgeFilter.has(e.data.relationship_type as string)
        if (edgeFilter) return false
        return true
      })
      .map((e: GraphEdge) => ({ group: 'edges' as const, data: e.data }))
    return [...nodes, ...edges]
  }, [rawNodes, rawEdges, filterEntityTypes, filterEdgeTypes])

  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null
    return rawNodes.find((n: GraphNode) => n.data.id === selectedNodeId)
  }, [rawNodes, selectedNodeId])

  const toggleEntityFilter = useCallback((t: string) => {
    setFilterEntityTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }, [])

  const toggleEdgeFilter = useCallback((t: string) => {
    setFilterEdgeTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }, [])

  const handleCy = useCallback((cy: Core) => {
    cy.on('tap', 'node', (ev) => {
      setSelectedNodeId(ev.target.id())
      setContextMenu(null)
    })
    cy.on('cxttap', 'node', (ev) => {
      const node = ev.target
      const data = node.data() as { doc_id?: string; label?: string }
      setContextMenu({
        x: ev.originalEvent.clientX,
        y: ev.originalEvent.clientY,
        nodeId: node.id(),
        docId: data.doc_id,
        label: data.label,
      })
    })
  }, [])

  if (!investigationId) {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-gray-500">
        No investigation selected
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-gray-500">
        A carregar grafo…
      </div>
    )
  }

  if (isError || data?.error) {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-red-600">
        Erro ao carregar grafo. {data?.error === 'not_found' ? 'Investigação não encontrada.' : ''}
      </div>
    )
  }

  if (!data?.elements || (data.elements.nodes.length === 0 && data.elements.edges.length === 0)) {
    return (
      <div className="rounded border border-gray-200 bg-white p-4 text-gray-500">
        Nenhum dado de grafo para esta investigação.
      </div>
    )
  }

  return (
    <div className="rounded border border-gray-200 bg-white overflow-hidden">
      <div className="flex flex-wrap gap-4 p-2 border-b border-gray-200 bg-gray-50">
        {entityTypes.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Entidades:</span>
            {entityTypes.map((t) => (
              <label key={t} className="inline-flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={filterEntityTypes.size === 0 || filterEntityTypes.has(t)}
                  onChange={() => toggleEntityFilter(t)}
                />
                {t}
              </label>
            ))}
          </div>
        )}
        {edgeTypes.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-700">Relações:</span>
            {edgeTypes.map((t) => (
              <label key={t} className="inline-flex items-center gap-1 text-sm">
                <input
                  type="checkbox"
                  checked={filterEdgeTypes.size === 0 || filterEdgeTypes.has(t)}
                  onChange={() => toggleEdgeFilter(t)}
                />
                {t}
              </label>
            ))}
          </div>
        )}
      </div>
      <div className="relative">
        <div className="w-full h-[500px]">
          <CytoscapeComponent
            elements={elements}
            style={{ width: '100%', height: '100%' }}
            layout={LAYOUT}
            cy={handleCy}
            stylesheet={[
              { selector: 'node', style: { label: 'data(label)', 'text-valign': 'bottom', 'text-margin-y': 4 } },
              { selector: 'edge', style: { 'curve-style': 'bezier', 'target-arrow-shape': 'triangle' } },
            ]}
          />
        </div>
        {contextMenu && (
          <div
            className="fixed z-50 bg-white border border-gray-200 rounded shadow-lg py-1 min-w-[160px]"
            style={{ left: contextMenu.x, top: contextMenu.y }}
          >
            <button
              type="button"
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100"
              onClick={() => {
                alert(
                  contextMenu.docId
                    ? `Documento: ${contextMenu.docId}\nEntidade: ${contextMenu.label ?? contextMenu.nodeId}`
                    : `Entidade: ${contextMenu.label ?? contextMenu.nodeId}\n(sem doc_id)`
                )
                setContextMenu(null)
              }}
            >
              Ver documento original
            </button>
            <button
              type="button"
              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100"
              onClick={() => setContextMenu(null)}
            >
              Fechar
            </button>
          </div>
        )}
      </div>
      {selectedNode && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-semibold text-gray-900">Detalhes da entidade</h3>
            <button type="button" className="text-gray-500 hover:text-gray-700" onClick={() => setSelectedNodeId(null)}>
              ✕
            </button>
          </div>
          <dl className="text-sm space-y-1">
            <dt className="text-gray-500">ID</dt>
            <dd className="text-gray-900">{selectedNode.data.id}</dd>
            <dt className="text-gray-500">Label</dt>
            <dd className="text-gray-900">{String(selectedNode.data.label ?? '')}</dd>
            {selectedNode.data.entity_type != null && (
              <>
                <dt className="text-gray-500">Tipo</dt>
                <dd className="text-gray-900">{String(selectedNode.data.entity_type)}</dd>
              </>
            )}
            {selectedNode.data.doc_id != null && (
              <>
                <dt className="text-gray-500">Doc ID</dt>
                <dd className="text-gray-900">{String(selectedNode.data.doc_id)}</dd>
              </>
            )}
            {selectedNode.data.text != null && (
              <>
                <dt className="text-gray-500">Texto</dt>
                <dd className="text-gray-900">{String(selectedNode.data.text)}</dd>
              </>
            )}
          </dl>
        </div>
      )}
    </div>
  )
}
