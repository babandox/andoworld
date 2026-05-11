import { create } from "zustand";

interface SelectionState {
  selectedTimelineEventId: string | null;
  selectedGraphNodeId: string | null;
  selectedMarkerId: string | null;
  selectedSourceId: string | null;
  relationFilters: Set<string>;
  selectTimelineEvent: (id: string | null, relatedNodeId?: string | null) => void;
  selectGraphNode: (id: string | null) => void;
  selectMarker: (id: string | null) => void;
  selectSource: (id: string | null) => void;
  clearSelection: () => void;
  toggleRelation: (relation: string) => void;
}

const DEFAULT_RELATIONS = new Set(["triggers", "escalates", "justifies", "disrupts"]);

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedTimelineEventId: null,
  selectedGraphNodeId: null,
  selectedMarkerId: null,
  selectedSourceId: null,
  relationFilters: DEFAULT_RELATIONS,
  selectTimelineEvent: (id, relatedNodeId) =>
    set({ selectedTimelineEventId: id, selectedGraphNodeId: relatedNodeId ?? null, selectedSourceId: null, selectedMarkerId: null }),
  selectGraphNode: (id) => set({ selectedGraphNodeId: id, selectedSourceId: null, selectedTimelineEventId: null }),
  selectMarker: (id) => set({ selectedMarkerId: id, selectedSourceId: null, selectedTimelineEventId: null }),
  selectSource: (id) => set({ selectedSourceId: id, selectedTimelineEventId: null, selectedGraphNodeId: null, selectedMarkerId: null }),
  clearSelection: () => set({ selectedTimelineEventId: null, selectedGraphNodeId: null, selectedMarkerId: null, selectedSourceId: null }),
  toggleRelation: (relation) =>
    set((state) => {
      const next = new Set(state.relationFilters);
      if (next.has(relation)) {
        next.delete(relation);
      } else {
        next.add(relation);
      }
      return { relationFilters: next };
    })
}));
