import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import { SyncStatus, StatusAndProgress, StatusUpdate } from "../models/syncStatus";

export interface DatasetTabsState {
    objSyncStatus: SyncStatus;
    simplificationStatus: StatusAndProgress;
}

const initialState: DatasetTabsState = {
    objSyncStatus: SyncStatus.None,
    simplificationStatus: {
        progress: '',
        status: ''
    }
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
        }
    }
})

export const {
    updateDatasetTabStatuses,
    resetDatasetTabStatuses
} = datasetTabsSlice.actions
export default datasetTabsSlice.reducer;