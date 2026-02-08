import { apiGet, apiPost } from './client'
import type { Investigation } from '../types'

export interface InvestigationsResponse {
  investigations: Array<{ investigation_id: string; name?: string; created_at?: string }>
}

export function fetchInvestigations() {
  return apiGet<InvestigationsResponse>('/investigations')
}

export function fetchInvestigation(id: string) {
  return apiGet<Investigation & { error?: string }>(`/investigations/${id}`)
}

export function createInvestigation(body?: { name?: string; uploads_path?: string }) {
  return apiPost<{ investigation_id: string; status: string; message?: string }>('/investigations', body)
}

export function runInvestigation(id: string) {
  return apiPost<{ status: string; investigation_id: string; error?: string }>(`/investigations/${id}/run`)
}
