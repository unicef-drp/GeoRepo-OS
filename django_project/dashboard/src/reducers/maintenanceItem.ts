import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {RootState} from "../app/store";

export interface MaintenanceItemState {
  hasMaintenance: boolean,
  maintenanceMessage: string,
  maintenanceId: number,
  maintenanceScheduledDate?: Date
}
  
const initialState: MaintenanceItemState = {
  hasMaintenance:  false,
  maintenanceMessage: '',
  maintenanceId: 0
}

export const maintenanceItemSlice = createSlice({
    name: 'maintenanceItem',
    initialState,
    reducers: {
      setMaintenanceItem: (state, action: PayloadAction<MaintenanceItemState>) => {
        if (action.payload.hasMaintenance && state.maintenanceId == action.payload.maintenanceId) return;
        state.hasMaintenance = action.payload.hasMaintenance
        state.maintenanceMessage = action.payload.maintenanceMessage
        state.maintenanceId = action.payload.maintenanceId
        state.maintenanceScheduledDate = action.payload.maintenanceScheduledDate
      },
      removeMaintenanceItem: (state, action: PayloadAction<boolean>) => {
        state.hasMaintenance = false
        state.maintenanceMessage = ''
        state.maintenanceId = 0
        state.maintenanceScheduledDate = null
      }
    }
})
  
export const {
  setMaintenanceItem,
  removeMaintenanceItem
} = maintenanceItemSlice.actions

export default maintenanceItemSlice.reducer;

export const hasMaintenance = (state: RootState) => state.maintenanceItem.hasMaintenance
export const maintenanceMessage = (state: RootState) => state.maintenanceItem.maintenanceMessage
export const maintenanceId = (state: RootState) => state.maintenanceItem.maintenanceId
export const maintenanceScheduledDate = (state: RootState) => state.maintenanceItem.maintenanceScheduledDate