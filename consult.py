import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import time
import requests
import pandas as pd
from io import StringIO
from pathlib import Path
from datetime import datetime

from state_manager import (
    deja_traite, marquer_pending, marquer_in_progress,
    marquer_done, marquer_error, state_coll
)
from hdfs_utils import upload_to_hdfs
from mongo_utils import get_all_bce_numbers

TMP = Path("tmp/pdfs")
TMP.mkdir(parents=True, exist_ok=True)

TMP_HOTELLERIE = Path("tmp/hotellerie")
TMP_HOTELLERIE.mkdir(parents=True, exist_ok=True)

BASE = "https://consult.cbso.nbb.be/api"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
}


def make_session(enterprise_number: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    page_url = f"https://consult.cbso.nbb.be/consult-enterprise/{enterprise_number}"
    session.headers.update({"Referer": page_url})
    session.get(page_url, timeout=15)
    return session


def get_deposits(session: requests.Session, enterprise_number: str) -> list:
    url = (
        f"{BASE}/rs-consult/published-deposits"
        f"?page=0&size=10&enterpriseNumber={enterprise_number}"
        f"&sort=periodEndDate,desc&sort=depositDate,desc"
    )
    r = session.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    print(f"Found {data['totalElements']} filings ({data['totalPages']} pages). Loading first {len(data['content'])}.")
    return data["content"]


def download_csv(session: requests.Session, deposit_id: str) -> str:
    url = f"{BASE}/external/broker/public/deposits/consult/csv/{deposit_id}"
    r = session.get(url, timeout=15)
    r.raise_for_status()
    return r.text


def download_pdf(session: requests.Session, deposit: dict) -> Path:
    """Télécharge le PDF d'un dépôt, l'upload vers HDFS Bronze, met à jour la State DB."""
    deposit_id  = deposit["id"]
    year        = deposit["periodEndDateYear"]
    enterprise  = deposit["enterpriseNumber"]
    reference   = deposit["reference"]
    filename    = f"{enterprise}_{year}_{reference}.pdf"
    dest        = TMP / filename

    if deja_traite(enterprise, deposit_id, "comptes_annuels"):
        print(f"    Deja traite (state DB) : {filename}")
        return dest

    marquer_pending(enterprise, deposit_id, "comptes_annuels", annee=year)

    try:
        url = f"{BASE}/external/broker/public/deposits/pdf/{deposit_id}"
        r = session.get(url, timeout=30)
        r.raise_for_status()
        dest.write_bytes(r.content)

        hdfs_path = upload_to_hdfs(str(dest), f"/bronze/nbb/{enterprise}")
        marquer_done(enterprise, deposit_id, "comptes_annuels", chemin_hdfs=hdfs_path)
        print(f"    PDF saved + HDFS : {filename} -> {hdfs_path}")
        return dest
    except Exception as e:
        marquer_error(enterprise, deposit_id, "comptes_annuels", str(e))
        print(f"    Echec PDF pour {year}: {e}")
        return None


def parse_csv(csv_text: str) -> dict:
    df = pd.read_csv(StringIO(csv_text), header=None, skiprows=1)
    codes = {}
    for _, row in df.iterrows():
        key = str(row[0]).strip()
        try:
            codes[key] = float(row[1])
        except (ValueError, TypeError):
            codes[key] = row[1]
    return codes


def compute_kpis(codes: dict) -> dict:
    def get(code):
        return codes.get(code, 0.0)

    omzet        = get("70")
    cogs         = get("60")
    depreciation = get("630")
    ebit         = get("9901")
    net_profit   = get("9904")
    cash         = get("54/58")
    equity       = get("10/15")
    total_assets = get("20/58")
    fin_debt     = get("17") + get("43")
    gross_profit = omzet - cogs
    ebitda       = ebit + depreciation

    def pct(num, denom):
        return round(num / denom * 100, 2) if denom else None

    return {
        "entity":           codes.get("Entity name"),
        "period_end":       codes.get("Accounting period end date"),
        "chiffre_affaires": omzet,
        "marge_brute":      gross_profit,
        "ebitda":           ebitda,
        "ebit":             ebit,
        "resultat_net":     net_profit,
        "taux_marge_brute": pct(gross_profit, omzet),
        "taux_ebitda":      pct(ebitda, omzet),
        "marge_nette":      pct(net_profit, omzet),
        "tresorerie":       cash,
        "dettes_fin":       fin_debt,
        "dette_nette":      fin_debt - cash,
        "fonds_propres":    equity,
        "total_actif":      total_assets,
        "autonomie_fin":    pct(equity, total_assets),
    }


def get_all_kpis(enterprise_number: str) -> list[dict]:
    session = make_session(enterprise_number)
    deposits = get_deposits(session, enterprise_number)

    results = []
    for deposit in deposits:
        deposit_id = deposit["id"]
        year = deposit["periodEndDateYear"]

        print(f"  Processing {year} (id={deposit_id})...")

        download_pdf(session, deposit)
        time.sleep(0.5)

        if deposit.get("migration"):
            print(f"    Skipping CSV for {year} (legacy/migrated filing)")
            continue

        try:
            csv_text = download_csv(session, deposit_id)
            codes = parse_csv(csv_text)
            kpis = compute_kpis(codes)
            kpis["year"] = year
            kpis["reference"] = deposit["reference"]
            results.append(kpis)
        except Exception as e:
            print(f"    Echec CSV pour {year}: {e}")
        time.sleep(0.5)

    return results


def run_for_all_enterprises():
    """Lit tous les BCE depuis MongoDB et lance get_all_kpis() pour chacun,
    avec gestion des coupures réseau temporaires."""
    bce_list = get_all_bce_numbers()
    print(f"{len(bce_list)} entreprises trouvees dans MongoDB.")

    traitees, erreurs = 0, 0

    for i, bce in enumerate(bce_list, start=1):
        print(f"\n{'='*50}\n[{i}/{len(bce_list)}] BCE {bce}")
        try:
            get_all_kpis(bce)
            traitees += 1
        except requests.exceptions.ConnectTimeout:
            print(f"  Timeout reseau pour {bce} -- pause 20s puis on continue")
            erreurs += 1
            time.sleep(20)
        except requests.exceptions.ConnectionError as e:
            print(f"  Erreur de connexion pour {bce} : {e} -- pause 20s")
            erreurs += 1
            time.sleep(20)
        except Exception as e:
            print(f"  Erreur generale pour {bce} : {e}")
            erreurs += 1

        time.sleep(1)

    print(f"\nTermine : {traitees} entreprises traitees, {erreurs} erreurs.")


# ============================================================
# SECTION HOTELLERIE — Jour 2, Part 2
# ============================================================

TYPE_DOC_HOTELLERIE = "comptes_annuels_hotellerie"
ANNEE_MIN_HOTELLERIE = 2021


def get_pending_hotellerie() -> list[dict]:
    """Retourne les entreprises hôtelières encore en 'pending' dans download_state."""
    return list(state_coll.find(
        {"type_document": TYPE_DOC_HOTELLERIE, "statut": "pending"},
        {"bce_number": 1, "_id": 0}
    ))


def download_csv_hotellerie(session: requests.Session, enterprise: str, deposit: dict) -> str | None:
    """Télécharge et uploade le CSV d'un dépôt hôtelier vers /bronze/hotellerie/{bce}/{year}/{ref}."""
    deposit_id = deposit["id"]
    year       = deposit["periodEndDateYear"]
    reference  = deposit["reference"]

    if deposit.get("migration"):
        print(f"    Skip CSV {year} (legacy/migrated filing, pas de CSV disponible)")
        return None

    try:
        csv_text = download_csv(session, deposit_id)

        filename = f"{enterprise}_{year}_{reference}.csv"
        local_path = TMP_HOTELLERIE / filename
        local_path.write_text(csv_text, encoding="utf-8")

        hdfs_dir = f"/bronze/hotellerie/{enterprise}/{year}"
        hdfs_path = upload_to_hdfs(str(local_path), hdfs_dir)

        print(f"    CSV saved + HDFS : {filename} -> {hdfs_path}")
        return hdfs_path
    except Exception as e:
        print(f"    Echec CSV {year} (ref={reference}): {e}")
        return None


def scrape_entreprise_hotellerie(session: requests.Session, bce: str) -> int:
    """Scrape les dépôts >= 2021 d'une entreprise hôtelière. Retourne le nombre de CSV réussis."""
    deposits = get_deposits(session, bce)

    deposits_recents = [
        d for d in deposits
        if d.get("periodEndDateYear") and int(d["periodEndDateYear"]) >= ANNEE_MIN_HOTELLERIE
    ]
    print(f"  {len(deposits_recents)} depot(s) >= {ANNEE_MIN_HOTELLERIE} sur {len(deposits)} au total")

    filings_count = 0
    for deposit in deposits_recents:
        year = deposit["periodEndDateYear"]
        print(f"  Processing {year} (id={deposit['id']})...")
        hdfs_path = download_csv_hotellerie(session, bce, deposit)
        if hdfs_path:
            filings_count += 1
        time.sleep(0.5)

    return filings_count


def run_hotellerie_scraping():
    """Scrape les entreprises hôtelières marquées 'pending' dans download_state,
    filtre les dépôts >= 2021, uploade les CSV vers /bronze/hotellerie/..., met à jour la State DB."""
    entreprises = get_pending_hotellerie()
    print(f"{len(entreprises)} entreprises hotellerie en attente (pending).")

    traitees, erreurs = 0, 0

    for i, ent in enumerate(entreprises, start=1):
        bce = ent["bce_number"]
        print(f"\n{'='*50}\n[{i}/{len(entreprises)}] BCE {bce}")

        marquer_in_progress(bce, "ALL", TYPE_DOC_HOTELLERIE)

        try:
            session = make_session(bce)
            filings_count = scrape_entreprise_hotellerie(session, bce)

            marquer_done(bce, "ALL", TYPE_DOC_HOTELLERIE, filings_count=filings_count)
            print(f"  -> Termine : {filings_count} depot(s) scrape(s) avec succes")
            traitees += 1

        except requests.exceptions.ConnectTimeout:
            marquer_error(bce, "ALL", TYPE_DOC_HOTELLERIE, "Timeout reseau")
            print(f"  Timeout reseau pour {bce} -- pause 20s")
            erreurs += 1
            time.sleep(20)
        except requests.exceptions.ConnectionError as e:
            marquer_error(bce, "ALL", TYPE_DOC_HOTELLERIE, str(e))
            print(f"  Erreur de connexion pour {bce} : {e} -- pause 20s")
            erreurs += 1
            time.sleep(20)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                marquer_pending(bce, "ALL", TYPE_DOC_HOTELLERIE)  # remis en pending pour reprise ulterieure
                print(f"  429 Too Many Requests -- arret du run, {bce} remis en pending. Relancer plus tard.")
                erreurs += 1
                break
            else:
                marquer_error(bce, "ALL", TYPE_DOC_HOTELLERIE, str(e))
                print(f"  Erreur HTTP pour {bce} : {e}")
                erreurs += 1
        except Exception as e:
            marquer_error(bce, "ALL", TYPE_DOC_HOTELLERIE, str(e))
            print(f"  Erreur generale pour {bce} : {e}")
            erreurs += 1

        time.sleep(2)

    print(f"\nTermine : {traitees} entreprises traitees, {erreurs} erreurs.")


if __name__ == "__main__":
    run_hotellerie_scraping()