import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchInvestigation } from '../api/investigations'
import { PipelineMonitor } from '../components/PipelineMonitor'
import { GraphExplorer } from '../components/GraphExplorer'

export default function Investigation() {
  const { id } = useParams<{ id: string }>()
  const { data: inv, isLoading } = useQuery({
    queryKey: ['investigation', id],
    queryFn: () => fetchInvestigation(id!),
    enabled: !!id,
  })

  if (!id) return <div className="p-6">Missing investigation ID</div>
  if (isLoading) return <div className="p-6">A carregar…</div>
  if (inv?.error) return <div className="p-6 text-red-600">Erro: {inv.error}</div>

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <nav className="mb-4">
        <Link to="/" className="text-blue-600 hover:underline">← Dashboard</Link>
      </nav>
      <h1 className="text-2xl font-bold text-gray-900 mb-2">{inv?.name ?? id}</h1>
      <p className="text-gray-600 mb-6">Documentos: {inv?.doc_count ?? 0} · Entidades: {inv?.entity_count ?? 0}</p>
      <section className="mb-8">
        <h2 className="text-lg font-semibold mb-2">Pipeline</h2>
        <PipelineMonitor investigationId={id} />
      </section>
      <section>
        <h2 className="text-lg font-semibold mb-2">Grafo</h2>
        <GraphExplorer investigationId={id} />
      </section>
    </div>
  )
}
