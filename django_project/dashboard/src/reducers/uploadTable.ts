import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {getDefaultFilter, UploadFilterInterface} from "../views/Upload/UploadFilter"
import {RootState} from "../app/store";


export interface TableState {
  currentColumns: string[];
  currentFilters: UploadFilterInterface;
  availableFilters: UploadFilterInterface;
}

const initialState: TableState = {
  currentColumns: [
    'id',
    'level_0_entity',
    'dataset',
    'type',
    'uploaded_by',
    'status'
  ],
  currentFilters: getDefaultFilter(),
  availableFilters: getDefaultFilter()
};

export const uploadTableSlice = createSlice({
  name: 'uploadTable',
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
} = uploadTableSlice.actions

export default uploadTableSlice.reducer;

export const currentColumns = (state: RootState) => state.uploadTable.currentColumns
export const currentFilters = (state: RootState) => state.uploadTable.currentFilters
export const availableFilters = (state: RootState) => state.uploadTable.availableFilters