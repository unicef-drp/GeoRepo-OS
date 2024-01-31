import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {getDefaultFilter, ViewSyncFilterInterface} from "../models/syncStatus"
import {RootState} from "../app/store";


export interface TableState {
  currentColumns: string[];
  currentFilters: ViewSyncFilterInterface;
  availableFilters: ViewSyncFilterInterface;
}

const initialState: TableState = {
  currentColumns: [
    'name',
    'is_tiling_config_match',
    'vector_tile_sync_status'
  ],
  currentFilters: getDefaultFilter(),
  availableFilters: getDefaultFilter()
};

export const viewSyncTableSlice = createSlice({
  name: 'viewSyncTable',
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
} = viewSyncTableSlice.actions

export default viewSyncTableSlice.reducer;

export const currentColumns = (state: RootState) => state.viewSyncTable.currentColumns
export const currentFilters = (state: RootState) => state.viewSyncTable.currentFilters
export const availableFilters = (state: RootState) => state.viewSyncTable.availableFilters