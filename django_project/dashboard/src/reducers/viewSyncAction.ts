import {createSlice, PayloadAction} from "@reduxjs/toolkit";
// import { ActiveBatchAction } from "../models/viewSync";


export interface ViewSyncActionState {
    isBatchActionAvailable: boolean;
    isBatchAction: boolean;
    selectedViews: number[];
    updatedAt: Date;
    rowsSelectedInPage: number[];
}

const initialState: ViewSyncActionState = {
    isBatchActionAvailable: true,
    isBatchAction: false,
    selectedViews: [],
    updatedAt: null,
    rowsSelectedInPage: []
}

export const viewSyncActionSlice = createSlice({
    name: 'viewSyncAction',
    initialState,
    reducers: {
        toggleIsBatchAction: (state, action: PayloadAction<string>) => {
            state.isBatchAction = !state.isBatchAction
            if (!state.isBatchAction) {
                state.selectedViews = []
                state.rowsSelectedInPage = []
            }
        },
        setIsBatchActionAvailable: (state, action: PayloadAction<boolean>) => {
            state.isBatchActionAvailable = action.payload
        },
        setSelectedViews: (state, action: PayloadAction<any>) => {
            let _selection = action.payload[0]
            let _data =  action.payload[1]
            let _result = []
            for (let i=0; i<_data.length; i++) {
                if (_selection.includes(_data[i].id)) {
                    _result.push(i)
                }
            }
            state.selectedViews = [..._selection]
            state.rowsSelectedInPage = _result
        },
        addSelectedView: (state, action: PayloadAction<number>) => {
            if (state.selectedViews.indexOf(action.payload) === -1){
                state.selectedViews = [
                    ...state.selectedViews,
                    action.payload
                ]
            }
        },
        removeSelectedView: (state, action: PayloadAction<number>) => {
            state.selectedViews = state.selectedViews.filter(a => a !== action.payload)
        },
        resetSelectedViews: (state, action: PayloadAction<null>) => {
            state.selectedViews = []
            state.rowsSelectedInPage = []
        },
        updateRowsSelectedInPage: (state, action: PayloadAction<any[]>) => {
            let _result = []
            for (let i=0; i<action.payload.length; i++) {
                if (state.selectedViews.includes(action.payload[i].id)) {
                    _result.push(i)
                }
            }
            state.rowsSelectedInPage = _result
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
    addSelectedView,
    removeSelectedView,
    resetSelectedViews,
    updateRowsSelectedInPage,
    onBatchActionSubmitted
} = viewSyncActionSlice.actions

export default viewSyncActionSlice.reducer;
