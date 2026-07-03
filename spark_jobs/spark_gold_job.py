from pyspark.sql import SparkSession
from pymongo import MongoClient
from datetime import datetime, timezone
import re

HDFS_BASE = "hdfs://namenode:9000/bronze/hotellerie"
MONGO_URI = "mongodb://admin:motdepasse@mongodb:27017/"
DB_NAME = "kbo_db"

spark = SparkSession.builder \
    .appName("KBO_Gold_Hotellerie") \
    .master("local[*]") \
    .getOrCreate()

sc = spark.sparkContext


def parse_pcmn_csv(text: str) -> dict:
    """Parse un CSV NBB (codes PCMN;valeur ou codes,valeur) en dict {code: float}."""
    sep = ";" if ";" in text.splitlines()[0] else ","
    codes = {}
    lines = text.strip().splitlines()[1:]  # skip header
    for line in lines:
        parts = line.split(sep)
        if len(parts) < 2:
            continue
        code = parts[0].strip().strip('"')
        raw_val = parts[1].strip().strip('"')
        try:
            codes[code] = float(raw_val.replace(",", "."))
        except ValueError:
            continue
    return codes


def get_val(codes: dict, *candidates) -> float:
    """Retourne la première valeur trouvée parmi les codes candidats (priorité au premier)."""
    for c in candidates:
        if c in codes:
            return codes[c]
    return 0.0


def get_range_sum(codes: dict, start: int, end: int) -> float:
    """Somme les codes numériques dans une plage (ex: 10 à 15)."""
    total = 0.0
    for code, val in codes.items():
        m = re.match(r"^(\d+)", code)
        if m and start <= int(m.group(1)) <= end:
            total += val
    return total


def extract_year_and_ref(hdfs_path: str) -> tuple[str, str, str]:
    """Extrait bce, year, reference depuis un chemin HDFS /bronze/hotellerie/{bce}/{year}/{file}.csv"""
    parts = hdfs_path.replace("hdfs://namenode:9000", "").strip("/").split("/")
    # parts = ['bronze', 'hotellerie', bce, year, filename.csv]
    bce = parts[2]
    year = parts[3]
    filename = parts[4]
    reference = filename.replace(".csv", "")
    return bce, year, reference


def compute_ratios(codes: dict) -> dict:
    ca            = get_val(codes, "70")
    achats        = get_val(codes, "60")
    variation     = get_val(codes, "71")
    ebit          = get_val(codes, "9901")
    resultat_net  = get_val(codes, "9904")

    tresorerie = get_val(codes, "54/58") or (get_val(codes, "54") + get_val(codes, "55"))
    dettes_fin = get_val(codes, "17") + get_val(codes, "43")
    fonds_propres = get_val(codes, "10/15") or get_range_sum(codes, 10, 15)
    capital_souscrit = get_val(codes, "100")

    marge_brute = ca - achats + variation
    marge_nette = round(resultat_net / ca * 100, 2) if ca else None
    roe = round(resultat_net / fonds_propres * 100, 2) if fonds_propres else None
    ratio_liquidite = round(tresorerie / dettes_fin, 2) if dettes_fin else None
    taux_endettement = round(dettes_fin / fonds_propres * 100, 2) if fonds_propres else None

    return {
        "ca": ca,
        "achats": achats,
        "variation_stocks": variation,
        "ebit": ebit,
        "resultat_net": resultat_net,
        "tresorerie": tresorerie,
        "dettes_financieres": dettes_fin,
        "fonds_propres": fonds_propres,
        "capital_souscrit": capital_souscrit,
        "marge_brute": marge_brute,
        "ratios": {
            "marge_nette_pct": marge_nette,
            "roe_pct": roe,
            "ratio_liquidite": ratio_liquidite,
            "taux_endettement_pct": taux_endettement,
        }
    }


def process_all_csvs():
    """Lit tous les CSV sous /bronze/hotellerie, calcule les ratios, groupe par entreprise."""
    rdd = sc.wholeTextFiles(f"{HDFS_BASE}/*/*/*.csv")
    print(f"Fichiers trouves : {rdd.count()}")

    def parse_row(entry):
        path, content = entry
        bce, year, reference = extract_year_and_ref(path)
        codes = parse_pcmn_csv(content)
        year_data = compute_ratios(codes)
        year_data["year"] = int(year)
        year_data["reference"] = reference
        return (bce, year_data)

    parsed = rdd.map(parse_row)
    grouped = parsed.groupByKey().mapValues(list).collect()

    return grouped


def upsert_gold(grouped_results):
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    gold_coll = db["hotel_gold"]

    now = datetime.now(timezone.utc)
    updated = 0

    for bce, years_list in grouped_results:
        years_sorted = sorted(years_list, key=lambda y: y["year"], reverse=True)

        gold_coll.update_one(
            {"enterprise_number": bce},
            {
                "$set": {
                    "enterprise_number": bce,
                    "years": years_sorted,
                    "schema_type": "full",  # a affiner si l'info est disponible dans le CSV
                    "last_updated": now,
                }
            },
            upsert=True
        )
        updated += 1

    print(f"hotel_gold mis a jour : {updated} entreprises.")
    gold_coll.create_index("enterprise_number", unique=True)


if __name__ == "__main__":
    results = process_all_csvs()
    upsert_gold(results)
    spark.stop()