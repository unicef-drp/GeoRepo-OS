import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {getDefaultFilter, ReviewFilterInterface} from "../views/Review/Filter"
import {RootState} from "../app/store";


export interface TableState {
  currentColumns: string[];
  currentFilters: ReviewFilterInterface;
  availableFilters: ReviewFilterInterface;
}

const initialState: TableState = {
  currentColumns: [
    'level_0_entity',
    'upload',
    'dataset',
    'start_date',
    'revision',
    'status',
    'submitted_by'
  ],
  currentFilters: getDefaultFilter(),
  availableFilters: getDefaultFilter()
};

export const reviewTableSlice = createSlice({
  name: 'reviewTable',
  initialState,
  reducers: {
    setCurrentColumns: (state, action: PayloadAction<string>) => {
      state.currentColumns = JSON.parse(action.payload)
    },
    setCurrentFilters: (state, action: PayloadAction<string>) => {
      state.currentFilters = JSON.parse(action.payload)
    },
    setAvailableFilters: (state, action: PayloadAction<string>) => {
      state.availableFilters = JSON.parse(action.payload)
    }
  }
})

export const {
  setCurrentColumns,
  setCurrentFilters,
  setAvailableFilters
} = reviewTableSlice.actions

export default reviewTableSlice.reducer;

export const currentColumns = (state: RootState) => state.reviewTable.currentColumns
export const currentFilters = (state: RootState) => state.reviewTable.currentFilters
export const availableFilters = (state: RootState) => state.reviewTable.availableFilters