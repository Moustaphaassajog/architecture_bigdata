from pymongo import MongoClient, ASCENDING

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
state_coll = db["download_state"]

# Si l'ancien index (sans type_document) existe, on le supprime
existing_indexes = state_coll.index_information()
if "uniq_bce_deposit" in existing_indexes:
    state_coll.drop_index("uniq_bce_deposit")
    print("Ancien index 'uniq_bce_deposit' supprimé.")

state_coll.create_index(
    [("bce_number", ASCENDING), ("deposit_id", ASCENDING), ("type_document", ASCENDING)],
    unique=True,
    name="uniq_bce_deposit_type"
)
state_coll.create_index([("statut", ASCENDING)])
state_coll.create_index([("annee", ASCENDING)])
state_coll.create_index([("type_document", ASCENDING)])

print("Collection 'download_state' initialisée.")
print("Index actuels :", state_coll.index_information())