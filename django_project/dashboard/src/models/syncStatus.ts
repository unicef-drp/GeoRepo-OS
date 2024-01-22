export enum SyncStatus {
    None = "none",
    OutOfSync = "out_of_sync",
    Syncing = "syncing",
    Synced = "synced",
    Error = "error"
}

export interface StatusAndProgress {
    status: string;
    progress: string;
}

export interface StatusUpdate {
    objSyncStatus: SyncStatus,
    simplificationStatus: StatusAndProgress
}

export interface ViewSyncFilterInterface {
    is_tiling_config_match: string[],
    simplification_status: string[],
    vector_tile_sync_status: string[],
    search_text: string
}

export function getDefaultFilter():ViewSyncFilterInterface {
    return {
        is_tiling_config_match: [],
        simplification_status: [],
        vector_tile_sync_status: [],
        search_text: ''
    }
}

export const TILING_CONFIG_STATUS_FILTER = [
    'Tiling config matches dataset',
    'View uses custom tiling config'
]

export const SIMPLIFICATION_STATUS_FILTER = [
    'Out of Sync',
    'Syncing',
    'Terminated unexpectedly',
    'Done',
]

export const VECTOR_TILE_SYNC_STATUS_FILTER = [
    'Out of Sync',
    'Syncing',
    'Terminated unexpectedly',
    'Done',
]
