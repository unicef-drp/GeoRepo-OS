import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import { SyncStatus, StatusAndProgress } from "../models/syncStatus";

export interface ViewTabsState {
    tilingConfigSyncStatus: SyncStatus;
    simplificationStatus: StatusAndProgress;
    tilingStatus: StatusAndProgress;
}

const initialState: ViewTabsState = {
    tilingConfigSyncStatus: SyncStatus.None,
    simplificationStatus: {
        progress: '',
        status: ''
    },
    tilingStatus: {
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
        updateViewTabStatuses: (state, action: PayloadAction<StatusAndProgress[]>) => {
            let _simplification = action.payload[0]
            let _tiling = action.payload[1]

            state.simplificationStatus = {..._simplification}
            state.tilingStatus = {..._tiling}
            if (state.tilingConfigSyncStatus === SyncStatus.Syncing) {
                if (DONE_STATUS_LIST.includes(state.simplificationStatus.status) &&
                    DONE_STATUS_LIST.includes(state.tilingStatus.status)) {
                    if (state.simplificationStatus.status === 'Error' || state.tilingStatus.status === 'Error') {
                        state.tilingConfigSyncStatus = SyncStatus.Error
                    } else {
                        state.tilingConfigSyncStatus = SyncStatus.Synced
                    }
                }
            } else if (PROCESSING_STATUS_LIST.includes(state.simplificationStatus.status) || PROCESSING_STATUS_LIST.includes(state.tilingStatus.status)) {
                state.tilingConfigSyncStatus = SyncStatus.Syncing
            }
        },
        resetViewTabStatuses: (state, action: PayloadAction<null>) => {
            state.tilingConfigSyncStatus = SyncStatus.None
            state.simplificationStatus = {
                progress: '',
                status: ''
            }
            state.tilingStatus = {
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