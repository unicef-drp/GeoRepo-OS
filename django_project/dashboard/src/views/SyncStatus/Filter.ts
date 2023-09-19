export interface ViewSyncFilterInterface {
  sync_status: string[],
  search_text: string
}

export function getDefaultFilter():ViewSyncFilterInterface {
    return {
      sync_status: [],
      search_text: ''
    }
}