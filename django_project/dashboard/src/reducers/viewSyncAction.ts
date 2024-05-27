import {createSlice, PayloadAction} from "@reduxjs/toolkit";
// import { ActiveBatchAction } from "../models/viewSync";


export interface ViewSyncActionState {
    isBatchActionAvailable: boolean;
    isBatchAction: boolean;
    selectedViews: number[];
    updatedAt: Date;
    rowsSelectedInPage: number[];
    isCheckAll: boolean;
}

const initialState: ViewSyncActionState = {
    isBatchActionAvailable: true,
    isBatchAction: false,
    selectedViews: [],
    updatedAt: null,
    rowsSelectedInPage: [],
    isCheckAll: false
}

export interface RowSelectedUpdate {
    id: number;
    index: number;
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
        addSelectedView: (state, action: PayloadAction<RowSelectedUpdate>) => {
            if (state.selectedViews.indexOf(action.payload.id) === -1){
                state.selectedViews = [
                    ...state.selectedViews,
                    action.payload.id
                ]
            }
            state.rowsSelectedInPage = [...state.rowsSelectedInPage, action.payload.index]
        },
        removeSelectedView: (state, action: PayloadAction<RowSelectedUpdate>) => {
            state.selectedViews = state.selectedViews.filter(a => a !== action.payload.id)
            state.rowsSelectedInPage = state.rowsSelectedInPage.filter(a => a !== action.payload.index)
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
            state.isCheckAll = false
            state.selectedViews = []
            state.rowsSelectedInPage = []
        },
        setIsCheckAll: (state, action: PayloadAction<boolean>) => {
            state.isCheckAll = action.payload
            if (!state.isCheckAll) {
                state.selectedViews = []
                state.rowsSelectedInPage = []
            }
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
    onBatchActionSubmitted,
    setIsCheckAll
} = viewSyncActionSlice.actions

export default viewSyncActionSlice.reducer;
