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
