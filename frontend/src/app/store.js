import { configureStore } from "@reduxjs/toolkit";
import entrepriseReducer from "../features/entreprise/entrepriseSlice";

export const store = configureStore({
  reducer: {
    entreprise: entrepriseReducer,
  },
});
