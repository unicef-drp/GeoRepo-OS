import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import { ActiveBatchReview, reviewTableRowInterface } from "../models/review";


export interface ReviewActionState {
    isBatchReviewAvailable: boolean;
    isBatchReview: boolean;
    selectedReviews: number[];
    pendingReviews: number[];
    currentReview: ActiveBatchReview;
    updatedAt: Date;
    rowsSelectedInPage: number[];
}

const initialState: ReviewActionState = {
    isBatchReviewAvailable: true,
    isBatchReview: false,
    selectedReviews: [],
    pendingReviews: [],
    rowsSelectedInPage: [],
    currentReview: {
        id: 0,
        submitted_by: '',
        submitted_at: '',
        is_approve: false,
        progress: '',
        status: ''
    },
    updatedAt: null
}

export const reviewActionSlice = createSlice({
    name: 'reviewAction',
    initialState,
    reducers: {
        toggleIsBatchReview: (state, action: PayloadAction<string>) => {
            state.isBatchReview = !state.isBatchReview
            if (!state.isBatchReview) {
                state.selectedReviews = []
                state.rowsSelectedInPage = []
            }
        },
        setIsBatchReviewAvailable: (state, action: PayloadAction<boolean>) => {
            state.isBatchReviewAvailable = action.payload
        },
        setSelectedReviews: (state, action: PayloadAction<any>) => {
            let _selection = action.payload[0]
            let _data =  action.payload[1]
            let _result = []
            for (let i=0; i<_data.length; i++) {
                if (_selection.includes(_data[i].id)) {
                    _result.push(i)
                }
            }
            state.selectedReviews = [..._selection]
            state.rowsSelectedInPage = _result
        },
        addSelectedReview: (state, action: PayloadAction<number>) => {
            if (state.selectedReviews.indexOf(action.payload) === -1){
                state.selectedReviews = [
                    ...state.selectedReviews,
                    action.payload
                ]
            }
        },
        removeSelectedReview: (state, action: PayloadAction<number>) => {
            state.selectedReviews = state.selectedReviews.filter(a => a !== action.payload)
        },
        resetSelectedReviews: (state, action: PayloadAction<null>) => {
            state.selectedReviews = []
            state.rowsSelectedInPage = []
        },
        setPendingReviews: (state, action: PayloadAction<number[]>) => {
            state.pendingReviews = [...action.payload]
        },
        updateRowsSelectedInPage: (state, action: PayloadAction<reviewTableRowInterface[]>) => {
            let _result = []
            for (let i=0; i<action.payload.length; i++) {
                if (state.selectedReviews.includes(action.payload[i].id)) {
                    _result.push(i)
                }
            }
            state.rowsSelectedInPage = _result
        },
        setCurrentReview: (state, action: PayloadAction<ActiveBatchReview>) => {
            state.currentReview = { ...action.payload }
            if (state.currentReview.id !== 0) {
                state.isBatchReviewAvailable = false
            } else {
                state.isBatchReviewAvailable = true
            }
        },
        onBatchReviewSubmitted: (state, action: PayloadAction<string>) => {
            state.updatedAt = new Date()
        }
    }
})

export const {
    toggleIsBatchReview,
    setIsBatchReviewAvailable,
    setSelectedReviews,
    setPendingReviews,
    setCurrentReview,
    onBatchReviewSubmitted,
    addSelectedReview,
    removeSelectedReview,
    resetSelectedReviews,
    updateRowsSelectedInPage
} = reviewActionSlice.actions

export default reviewActionSlice.reducer;
