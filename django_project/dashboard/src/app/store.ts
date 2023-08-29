import { configureStore, ThunkAction, Action } from '@reduxjs/toolkit';
import counterReducer from '../counter/counterSlice';
import breadcrumbReducer from "../reducers/breadcrumbMenu";
import moduleReducer from "../reducers/module"
import pollIntervalReducer from "../reducers/notificationPoll"
import maintenanceReducer from "../reducers/maintenanceItem"
import reviewActionReducer from "../reducers/reviewAction"
import reviewTableReducer from "../reducers/reviewTable"
import viewTableReducer from "../reducers/viewTable"
import uploadTableReducer from "../reducers/uploadTable"

export const store = configureStore({
  reducer: {
    counter: counterReducer,
    breadcrumb: breadcrumbReducer,
    module: moduleReducer,
    pollInterval: pollIntervalReducer,
    maintenanceItem: maintenanceReducer,
    reviewAction: reviewActionReducer,
    reviewTable: reviewTableReducer,
    viewTable: viewTableReducer,
    uploadTable: uploadTableReducer
  },
});

export type AppDispatch = typeof store.dispatch;
export type RootState = ReturnType<typeof store.getState>;
export type AppThunk<ReturnType = void> = ThunkAction<
  ReturnType,
  RootState,
  unknown,
  Action<string>
>;
