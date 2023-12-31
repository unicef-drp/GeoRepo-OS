import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {RootState} from "../app/store";


export interface TableState {
  currentColumns: string[];
}

const initialState: TableState = {
  currentColumns: [
    'country',
    'type',
    'name',
    'default_code',
    'ucode',
    'rev',
    'status',
    'level',
  ]
};

export const entitiesTableSlice = createSlice({
  name: 'entitiesTable',
  initialState,
  reducers: {
    setCurrentColumns: (state, action: PayloadAction<string>) => {
      state.currentColumns = JSON.parse(action.payload)
    }
  }
})

export const {
  setCurrentColumns
} = entitiesTableSlice.actions

export default entitiesTableSlice.reducer;

export const currentColumns = (state: RootState) => state.entitiesTable.currentColumns