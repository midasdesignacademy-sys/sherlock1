import { apiGet } from './client'
import type { GraphElements } from '../types'

export interface GraphResponse {
  elements?: GraphElements
  error?: string
  investigation_id?: string
}

export function fetchInvestigationGraph(investigationId: string) {
  return apiGet<GraphResponse>(`/investigations/${investigationId}/graph`)
}
