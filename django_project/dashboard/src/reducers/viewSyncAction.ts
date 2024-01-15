import {createSlice, PayloadAction} from "@reduxjs/toolkit";
// import { ActiveBatchAction } from "../models/viewSync";


export interface ViewSyncActionState {
    isBatchActionAvailable: boolean;
    isBatchAction: boolean;
    selectedViews: number[];
    updatedAt: Date;
}

const initialState: ViewSyncActionState = {
    isBatchActionAvailable: true,
    isBatchAction: false,
    selectedViews: [],
    updatedAt: null
}

export const viewSyncActionSlice = createSlice({
    name: 'viewSyncAction',
    initialState,
    reducers: {
        toggleIsBatchAction: (state, action: PayloadAction<string>) => {
            state.isBatchAction = !state.isBatchAction
            if (!state.isBatchAction) {
                state.selectedViews = []
            }
        },
        setIsBatchActionAvailable: (state, action: PayloadAction<boolean>) => {
            state.isBatchActionAvailable = action.payload
        },
        setSelectedViews: (state, action: PayloadAction<number[]>) => {
            state.selectedViews = [...action.payload]
        },
        onBatchActionSubmitted: (state, action: PayloadAction<string>) => {
            state.updatedAt = new Date()
        }
    }
})

export const {
    toggleIsBatchAction,
    setIsBatchActionAvailable,
    setSelectedViews,
    onBatchActionSubmitted
} = viewSyncActionSlice.actions

export default viewSyncActionSlice.reducer;
