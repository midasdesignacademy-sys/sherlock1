import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchInvestigations } from '../api/investigations'

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['investigations'],
    queryFn: fetchInvestigations,
  })

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">SHERLOCK Intelligence</h1>
      <p className="text-gray-600 mb-6">Dashboard – listagem de investigações.</p>
      {isLoading && <p className="text-gray-500">A carregar…</p>}
      {data?.investigations && (
        <ul className="space-y-2">
          {data.investigations.map((inv) => (
            <li key={inv.investigation_id}>
              <Link
                to={`/investigations/${inv.investigation_id}`}
                className="text-blue-600 hover:underline"
              >
                {inv.name ?? inv.investigation_id}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
