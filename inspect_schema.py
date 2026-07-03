from pymongo import MongoClient

MONGO_URI = "mongodb://admin:motdepasse@localhost:27017/"
client = MongoClient(MONGO_URI)
db = client["kbo_db"]

print("=== enterprise (Bronze brut) ===")
print(db["enterprise"].find_one())

print("\n=== entreprises_full (jointure actuelle) ===")
doc = db["entreprises_full"].find_one()
print("Champs top-level :", list(doc.keys()))
if doc.get("addresses"):
    print("\nExemple address :", doc["addresses"][0])
if doc.get("denominations"):
    print("\nExemple denomination :", doc["denominations"][0])
if doc.get("activities"):
    print("\nExemple activity :", doc["activities"][0])

print("\n=== code (référentiel labels) ===")
print(db["code"].find_one())
print("Categories distinctes dans code :", db["code"].distinct("Category")[:20])