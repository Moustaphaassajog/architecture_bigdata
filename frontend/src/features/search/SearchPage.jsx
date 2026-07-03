import { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://localhost:8000';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const navigate = useNavigate();

  const handleSearch = async (e) => {
    const value = e.target.value;
    setQuery(value);

    if (value.length < 2) {
      setResults([]);
      return;
    }

    try {
      const response = await axios.get(`${API_BASE}/entreprises/search`, {
        params: { q: value },
      });
      setResults(response.data);
    } catch (err) {
      console.error('Erreur recherche:', err);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Recherche entreprise hôtelière</h1>
      <input
        type="text"
        placeholder="Nom ou numéro BCE..."
        value={query}
        onChange={handleSearch}
        style={{ width: '100%', padding: '0.75rem', fontSize: '1rem' }}
      />

      <ul style={{ listStyle: 'none', padding: 0, marginTop: '1rem' }}>
        {results.map((r) => (
          <li
            key={r.enterprise_number}
            onClick={() => navigate(`/entreprise/${r.enterprise_number}`)}
            style={{
              padding: '0.75rem',
              borderBottom: '1px solid #ddd',
              cursor: 'pointer',
            }}
          >
            <strong>{r.denomination || 'Nom inconnu'}</strong>
            <div style={{ fontSize: '0.85rem', color: '#666' }}>
              BCE {r.enterprise_number} — {r.status_label} — {r.juridical_form_label}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}