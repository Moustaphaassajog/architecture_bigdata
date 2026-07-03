import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const API_BASE = "http://localhost:8000";

export const fetchFicheEntreprise = createAsyncThunk(
  "entreprise/fetchFiche",
  async (bce) => {
    const response = await axios.get(`${API_BASE}/entreprises/${bce}`);
    return response.data;
  },
);

const entrepriseSlice = createSlice({
  name: "entreprise",
  initialState: {
    fiche: null,
    loading: false,
    error: null,
    statuts: [],
    statutsLoading: false,
  },
  reducers: {
    addStatut: (state, action) => {
      state.statuts.push(action.payload);
    },
    resetStatuts: (state) => {
      state.statuts = [];
    },
    setStatutsLoading: (state, action) => {
      state.statutsLoading = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchFicheEntreprise.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchFicheEntreprise.fulfilled, (state, action) => {
        state.loading = false;
        state.fiche = action.payload;
      })
      .addCase(fetchFicheEntreprise.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  },
});

export const { addStatut, resetStatuts, setStatutsLoading } =
  entrepriseSlice.actions;
export default entrepriseSlice.reducer;
