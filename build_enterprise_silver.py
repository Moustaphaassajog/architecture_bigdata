from pymongo import MongoClient
from datetime import datetime

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]


def build_code_lookup() -> dict:
    """Construit un dict {(Category, Code): Description} pour les labels FR."""
    lookup = {}
    cursor = db["code"].find({"Language": "FR"}, {"Category": 1, "Code": 1, "Description": 1, "_id": 0})
    for doc in cursor:
        lookup[(doc["Category"], doc["Code"])] = doc["Description"]
    return lookup


def normalize_date(date_str):
    """Convertit DD-MM-YYYY -> YYYY-MM-DD. Retourne None si invalide/absent."""
    if not date_str or not isinstance(date_str, str):
        return None
    try:
        return datetime.strptime(date_str.strip(), "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def dedupe_activities(activities: list) -> list:
    """Deduplique sur (NaceVersion, NaceCode, Classification) exact."""
    seen = set()
    result = []
    for act in activities:
        key = (act.get("NaceVersion"), act.get("NaceCode"), act.get("Classification"))
        if key in seen:
            continue
        seen.add(key)
        result.append(act)
    return result


def filter_main_address(addresses: list) -> list:
    """Ne garde que l'adresse de type REGO (siège social)."""
    return [a for a in addresses if a.get("TypeOfAddress") == "REGO"]


def reorder_denominations(denominations: list) -> list:
    """Place la dénomination principale (TypeOfDenomination == '001') en premier."""
    primary = [d for d in denominations if d.get("TypeOfDenomination") == "001"]
    secondary = [d for d in denominations if d.get("TypeOfDenomination") != "001"]
    return primary + secondary


def add_labels(doc: dict, code_lookup: dict) -> dict:
    """Ajoute les labels FR à côté des codes bruts, sans supprimer les codes originaux."""
    doc["JuridicalFormLabel"] = code_lookup.get(("JuridicalForm", doc.get("JuridicalForm")))
    doc["StatusLabel"] = code_lookup.get(("Status", doc.get("Status")))

    for act in doc.get("activities", []):
        category = f"Nace{act.get('NaceVersion')}"
        act["NaceLabel"] = code_lookup.get((category, act.get("NaceCode")))

    return doc


def build_silver():
    code_lookup = build_code_lookup()
    print(f"{len(code_lookup)} entrées de labels chargées depuis 'code'.")

    source = db["entreprises_full"]
    target = db["enterprise_silver"]
    target.drop()  # repart propre à chaque run

    total = source.count_documents({})
    print(f"{total} documents à transformer depuis entreprises_full...")

    batch = []
    batch_size = 1000
    processed = 0

    for doc in source.find():
        doc["StartDate"] = normalize_date(doc.get("StartDate"))
        doc["activities"] = dedupe_activities(doc.get("activities", []))
        doc["addresses"] = filter_main_address(doc.get("addresses", []))
        doc["denominations"] = reorder_denominations(doc.get("denominations", []))
        doc = add_labels(doc, code_lookup)

        batch.append(doc)
        processed += 1

        if len(batch) >= batch_size:
            target.insert_many(batch)
            batch = []
            print(f"  {processed}/{total} traités...")

    if batch:
        target.insert_many(batch)

    print(f"Terminé : {processed} documents insérés dans 'enterprise_silver'.")

    target.create_index("EnterpriseNumber", unique=True)
    target.create_index("Status")
    target.create_index("activities.NaceCode")
    target.create_index("activities.Classification")
    print("Index créés sur enterprise_silver.")


if __name__ == "__main__":
    build_silver()