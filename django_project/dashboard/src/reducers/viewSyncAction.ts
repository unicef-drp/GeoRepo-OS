import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import { ActiveBatchReview } from "../models/review";


export interface ReviewActionState {
    isBatchReviewAvailable: boolean;
    isBatchReview: boolean;
    selectedReviews: number[];
    pendingReviews: number[];
    currentReview: ActiveBatchReview;
    updatedAt: Date;
}

const initialState: ReviewActionState = {
    isBatchReviewAvailable: true,
    isBatchReview: false,
    selectedReviews: [],
    pendingReviews: [],
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
            }
        },
        setIsBatchReviewAvailable: (state, action: PayloadAction<boolean>) => {
            state.isBatchReviewAvailable = action.payload
        },
        setSelectedReviews: (state, action: PayloadAction<number[]>) => {
            state.selectedReviews = [...action.payload]
        },
        setPendingReviews: (state, action: PayloadAction<number[]>) => {
            state.pendingReviews = [...action.payload]
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
    onBatchReviewSubmitted
} = reviewActionSlice.actions

export default reviewActionSlice.reducer;
