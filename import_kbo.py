import pandas as pd
from pymongo import MongoClient
import os

# --- Config ---
base_path = r"C:\Users\ingmo\OneDrive\Documents\Epssi\Master2_IPSSI\007_Architecture_BIGDATA\jour1\KboOpenData_0404_2026_06_28_Full"
mongo_uri = "mongodb://admin:motdepasse@localhost:27017/"
db_name = "kbo_db"

client = MongoClient(mongo_uri)
db = client[db_name]

for filename in os.listdir(base_path):
    if filename.endswith(".csv"):
        collection_name = os.path.splitext(filename)[0].lower()
        filepath = os.path.join(base_path, filename)

        print(f"Import de {filename} -> collection '{collection_name}'...")

        chunk_size = 50000
        total = 0
        for chunk in pd.read_csv(filepath, chunksize=chunk_size, dtype=str, low_memory=False):
            records = chunk.to_dict("records")
            if records:
                db[collection_name].insert_many(records)
            total += len(records)

        print(f"  -> {total} documents insérés dans '{collection_name}'")

print("Import terminé.")
print("Collections créées :", db.list_collection_names())