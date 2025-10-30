import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import { SyncStatus, StatusAndProgress, StatusUpdate } from "../models/syncStatus";

export interface DatasetTabsState {
    objSyncStatus: SyncStatus;
    simplificationStatus: StatusAndProgress;
    previewSession?: string | null;
}

const initialState: DatasetTabsState = {
    objSyncStatus: SyncStatus.None,
    simplificationStatus: {
        progress: '',
        status: ''
    },
    previewSession: null
}

const DONE_STATUS_LIST = ['Done', 'Error']
const PROCESSING_STATUS_LIST = ['Queued', 'Processing']

export const datasetTabsSlice = createSlice({
    name: 'datasetTabs',
    initialState,
    reducers: {
        updateDatasetTabStatuses: (state, action: PayloadAction<StatusUpdate>) => {
            state.simplificationStatus = {...action.payload.simplificationStatus}
            state.objSyncStatus = action.payload.objSyncStatus
        },
        resetDatasetTabStatuses: (state, action: PayloadAction<null>) => {
            state.objSyncStatus = SyncStatus.None
            state.simplificationStatus = {
                progress: '',
                status: ''
            }
        },
        setPreviewSession: (state, action: PayloadAction<string | null>) => {
            state.previewSession = action.payload
        }
    }
})

export const {
    updateDatasetTabStatuses,
    resetDatasetTabStatuses,
    setPreviewSession
} = datasetTabsSlice.actions
export default datasetTabsSlice.reducer;