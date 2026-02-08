export interface Investigation {
  investigation_id: string
  name?: string
  created_at?: string
  doc_count?: number
  entity_count?: number
  relationships_count?: number
}

export interface ActivityEvent {
  agent: string
  step: 'start' | 'end' | 'error'
  timestamp: string
  investigation_id?: string
  payload?: Record<string, unknown>
}

export interface StateEntity {
  text?: string
  entity_type?: string
  confidence?: number
  doc_id?: string
  [key: string]: unknown
}

export interface StateRelationship {
  source_entity_id: string
  target_entity_id: string
  relationship_type?: string
  [key: string]: unknown
}

export interface GraphNode {
  data: {
    id: string
    label: string
    entity_type?: string
    doc_id?: string
    text?: string
    [key: string]: unknown
  }
}

export interface GraphEdge {
  data: {
    id: string
    source: string
    target: string
    relationship_type?: string
    [key: string]: unknown
  }
}

export interface GraphElements {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
