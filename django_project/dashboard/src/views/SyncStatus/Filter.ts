export interface ViewSyncFilterInterface {
  dataset: string[],
  sync_status: string[],
  search_text: string
}

export function getDefaultFilter():ViewSyncFilterInterface {
    return {
      dataset: [],
      sync_status: [],
      search_text: ''
    }
}