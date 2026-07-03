import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SearchPage from './features/search/SearchPage';
import EntreprisePage from './features/entreprise/EntreprisePage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/entreprise/:bce" element={<EntreprisePage />} />
      </Routes>
    </BrowserRouter>
  );
}