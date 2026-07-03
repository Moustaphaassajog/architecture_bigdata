import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { fetchFicheEntreprise, addStatut, resetStatuts, setStatutsLoading } from './entrepriseSlice';

const API_BASE = 'http://localhost:8000';

export default function EntreprisePage() {
  const { bce } = useParams();
  const dispatch = useDispatch();
  const { fiche, loading, statuts, statutsLoading } = useSelector((state) => state.entreprise);

  useEffect(() => {
    dispatch(fetchFicheEntreprise(bce));
  }, [bce, dispatch]);

  const handleLoadStatuts = () => {
    dispatch(resetStatuts());
    dispatch(setStatutsLoading(true));

    const eventSource = new EventSource(`${API_BASE}/entreprises/${bce}/statuts`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'document') {
        dispatch(addStatut(data));
      } else if (data.type === 'end' || data.type === 'error') {
        dispatch(setStatutsLoading(false));
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      dispatch(setStatutsLoading(false));
      eventSource.close();
    };
  };

  if (loading) return <div style={{ padding: '2rem' }}>Chargement...</div>;
  if (!fiche) return <div style={{ padding: '2rem' }}>Entreprise non trouvée</div>;

  return (
    <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
      <h1>{fiche.denomination}</h1>
      <p>BCE {fiche.enterprise_number} — {fiche.status_label} — {fiche.juridical_form_label}</p>
      <p>Créée le {fiche.start_date}</p>

      {fiche.address && (
        <p>
          {fiche.address.StreetFR} {fiche.address.HouseNumber}, {fiche.address.Zipcode} {fiche.address.MunicipalityFR}
        </p>
      )}

      <h2>Activités</h2>
      <ul>
        {fiche.activities
          .filter((a) => a.classification === 'MAIN')
          .map((a, i) => (
            <li key={i}>{a.nace_code} — {a.label}</li>
          ))}
      </ul>

      <h2>Ratios financiers par année</h2>
      <table border="1" cellPadding="8" style={{ borderCollapse: 'collapse', width: '100%' }}>
        <thead>
          <tr>
            <th>Année</th>
            <th>CA</th>
            <th>Marge brute</th>
            <th>Résultat net</th>
            <th>Marge nette %</th>
            <th>ROE %</th>
            <th>Taux endettement %</th>
          </tr>
        </thead>
        <tbody>
          {fiche.years.map((y) => (
            <tr key={y.year}>
              <td>{y.year}</td>
              <td>{y.ca?.toLocaleString()}</td>
              <td>{y.marge_brute?.toLocaleString()}</td>
              <td>{y.resultat_net?.toLocaleString()}</td>
              <td>{y.ratios?.marge_nette_pct}</td>
              <td>{y.ratios?.roe_pct}</td>
              <td>{y.ratios?.taux_endettement_pct}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Statuts notariés</h2>
      <button onClick={handleLoadStatuts} disabled={statutsLoading}>
        {statutsLoading ? 'Chargement en cours...' : 'Charger les statuts'}
      </button>

      <ul>
        {statuts.map((s, i) => (
          <li key={i}>
            {s.deed_date} — {s.document_title} {s.downloaded ? '✓' : '✗'}
          </li>
        ))}
      </ul>
    </div>
  );
}