import { create } from 'zustand'

interface UIState {
  sidebarOpen: boolean
  selectedNodeId: string | null
  setSidebarOpen: (open: boolean) => void
  setSelectedNode: (id: string | null) => void
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  selectedNodeId: null,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setSelectedNode: (id) => set({ selectedNodeId: id }),
}))
