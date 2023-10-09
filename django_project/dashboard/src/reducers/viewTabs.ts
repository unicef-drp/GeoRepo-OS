import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import { SyncStatus, StatusAndProgress, StatusUpdate } from "../models/syncStatus";

export interface ViewTabsState {
    objSyncStatus: SyncStatus;
    simplificationStatus: StatusAndProgress;
}

const initialState: ViewTabsState = {
    objSyncStatus: SyncStatus.None,
    simplificationStatus: {
        progress: '',
        status: ''
    }
}

const DONE_STATUS_LIST = ['Done', 'Error']
const PROCESSING_STATUS_LIST = ['Queued', 'Processing']

export const viewTabsSlice = createSlice({
    name: 'viewTabs',
    initialState,
    reducers: {
        updateViewTabStatuses: (state, action: PayloadAction<StatusUpdate>) => {
            state.simplificationStatus = {...action.payload.simplificationStatus}
            state.objSyncStatus = action.payload.objSyncStatus
        },
        resetViewTabStatuses: (state, action: PayloadAction<null>) => {
            state.objSyncStatus = SyncStatus.None
            state.simplificationStatus = {
                progress: '',
                status: ''
            }
        }
    }
})

export const {
    updateViewTabStatuses,
    resetViewTabStatuses
} = viewTabsSlice.actions
export default viewTabsSlice.reducer;