import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {getDefaultFilter, ViewsFilterInterface} from "../views/View/ViewsFilter"
import {RootState} from "../app/store";


export interface TableState {
  currentColumns: string[];
  currentFilters: ViewsFilterInterface;
  availableFilters: ViewsFilterInterface;
}

const initialState: TableState = {
  currentColumns: [
    'name',
    'description',
    'tags',
    'dataset',
    'min_privacy',
    'max_privacy',
    'status'
  ],
  currentFilters: getDefaultFilter(),
  availableFilters: getDefaultFilter()
};

export const viewTableSlice = createSlice({
  name: 'viewTable',
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
} = viewTableSlice.actions

export default viewTableSlice.reducer;

export const currentColumns = (state: RootState) => state.viewTable.currentColumns
export const currentFilters = (state: RootState) => state.viewTable.currentFilters
export const availableFilters = (state: RootState) => state.viewTable.availableFilters