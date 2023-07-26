import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {RootState} from "../app/store";

export const FETCH_INTERVAL_NORMAL = 60
export const FETCH_INTERVAL_JOB = 5


export interface PollIntervalState {
  currentInterval: number
}
  
const initialState: PollIntervalState = {
  currentInterval:  FETCH_INTERVAL_NORMAL
}

export const pollIntervalSlice = createSlice({
    name: 'pollInterval',
    initialState,
    reducers: {
      setPollInterval: (state, action: PayloadAction<number>) => {
        state.currentInterval = action.payload
      }
    }
})
  
export const {
  setPollInterval
} = pollIntervalSlice.actions

export default pollIntervalSlice.reducer;

export const currentInterval = (state: RootState) => state.pollInterval.currentInterval