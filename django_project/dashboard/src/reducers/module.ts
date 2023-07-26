import {createSlice, PayloadAction} from "@reduxjs/toolkit";
import {RootState} from "../app/store";
import {modules} from "../modules";


export interface ModuleState {
  currentModule: string;
}

const initialState: ModuleState = {
  currentModule:  ''
};

export const moduleSlice = createSlice({
  name: 'module',
  initialState,
  reducers: {
    setModule: (state, action: PayloadAction<string>) => {
      if (!action.payload) {
        // Use first module if the module type is not provided
        state.currentModule = modules[0]
      } else {
        state.currentModule = action.payload
      }
    }
  }
})

export const {
  setModule
} = moduleSlice.actions

export default moduleSlice.reducer;

export const currentModule = (state: RootState) => state.module.currentModule
