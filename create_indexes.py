from pymongo import MongoClient, ASCENDING

mongo_uri = "mongodb://admin:motdepasse@localhost:27017/"
client = MongoClient(mongo_uri)
db = client["kbo_db"]

# Index unique sur la clé principale de enterprise
db["enterprise"].create_index([("EnterpriseNumber", ASCENDING)], unique=True)

# Index sur establishment
db["establishment"].create_index([("EnterpriseNumber", ASCENDING)])
db["establishment"].create_index([("EstablishmentNumber", ASCENDING)], unique=True)

# Index sur les collections liées par EntityNumber
for coll_name in ["address", "contact", "denomination", "activity"]:
    db[coll_name].create_index([("EntityNumber", ASCENDING)])

# Index sur branch
db["branch"].create_index([("EnterpriseNumber", ASCENDING)])

print("Index créés.")
for coll_name in db.list_collection_names():
    print(f"\n{coll_name} :")
    for idx in db[coll_name].index_information():
        print(f"  - {idx}")