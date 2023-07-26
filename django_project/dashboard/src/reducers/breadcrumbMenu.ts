import { createAsyncThunk, createSlice, PayloadAction } from '@reduxjs/toolkit';
import {RootState} from "../app/store";

export interface BreadcrumbMenuInterface {
  id: string;
  name: string;
  link?: string;
}

export interface BreadcrumbState {
  currentMenu: string;
  currentDataset?: string;
  menus?: BreadcrumbMenuInterface[]
}

const initialState: BreadcrumbState = {
  currentMenu:  '',
  menus: []
};

export const breadcrumbSlice = createSlice({
  name: 'breadcrumb',
  initialState,
  reducers: {
    changeCurrentMenu: (state, action: PayloadAction<string>) => {
      state.currentMenu = action.payload
    },
    changeCurrentDataset: (state, action: PayloadAction<string>) => {
      state.currentDataset = action.payload
    },
    updateMenu: (state, action: PayloadAction<BreadcrumbMenuInterface>) => {
      if (typeof state.menus === 'undefined') {
        return
      }
      let index = 0
      for (const menu of state.menus) {
        if (menu.id === action.payload.id) {
          state.menus[index] = action.payload;
          return;
        }
        index += 1
      }
    },
    changeMenu: (state, action: PayloadAction<BreadcrumbMenuInterface>) => {
      state.menus = [action.payload]
      state.currentMenu = action.payload.name
    },
    addMenu: (state, action: PayloadAction<BreadcrumbMenuInterface>) => {
      if (typeof state.menus === 'undefined') {
        state.menus = []
      }
      for (const menu of state.menus) {
        if (menu.id === action.payload.id) {
          return
        }
      }
      state.currentMenu = action.payload.name
      state.menus.push(action.payload)
    },
    revertMenu: (state, action: PayloadAction<string>) => {
       if (typeof state.menus === 'undefined') {
         return
       }
       let index = 0;
       for (const menu of state.menus) {
         if (menu.id === action.payload) {
           state.menus = state.menus.slice(0, index + 1)
           state.currentMenu = action.payload
           return;
         }
         index += 1
       }
    },
  }
});

export const {
  changeCurrentMenu, changeCurrentDataset, changeMenu,
  addMenu, revertMenu, updateMenu } = breadcrumbSlice.actions;

export default breadcrumbSlice.reducer;

// The function below is called a selector and allows us to select a value from
// the state. Selectors can also be defined inline where they're used instead of
// in the slice file. For example: `useSelector((state: RootState) => state.counter.value)`
export const breadcrumbMenus = (state: RootState) => state.breadcrumb.menus
export const currentDataset = (state: RootState) => state.breadcrumb.currentDataset
