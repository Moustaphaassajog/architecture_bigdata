from pymongo import MongoClient, ASCENDING

mongo_uri = "mongodb://admin:motdepasse@localhost:27017/"
client = MongoClient(mongo_uri)
db = client["kbo_db"]

print("Étape 1 : enrichissement des établissements...")

db["establishment"].aggregate([
    {"$lookup": {
        "from": "denomination",
        "localField": "EstablishmentNumber",
        "foreignField": "EntityNumber",
        "as": "denominations"
    }},
    {"$lookup": {
        "from": "address",
        "localField": "EstablishmentNumber",
        "foreignField": "EntityNumber",
        "as": "addresses"
    }},
    {"$lookup": {
        "from": "contact",
        "localField": "EstablishmentNumber",
        "foreignField": "EntityNumber",
        "as": "contacts"
    }},
    {"$lookup": {
        "from": "activity",
        "localField": "EstablishmentNumber",
        "foreignField": "EntityNumber",
        "as": "activities"
    }},
    {"$merge": {"into": "establishments_full", "whenMatched": "replace", "whenNotMatched": "insert"}}
], allowDiskUse=True)

print("  -> establishments_full créée.")

# Index nécessaire pour la jointure rapide à l'étape 2
db["establishments_full"].create_index([("EnterpriseNumber", ASCENDING)])

print("Étape 2 : enrichissement des entreprises + imbrication des établissements...")

db["enterprise"].aggregate([
    {"$lookup": {
        "from": "denomination",
        "localField": "EnterpriseNumber",
        "foreignField": "EntityNumber",
        "as": "denominations"
    }},
    {"$lookup": {
        "from": "address",
        "localField": "EnterpriseNumber",
        "foreignField": "EntityNumber",
        "as": "addresses"
    }},
    {"$lookup": {
        "from": "contact",
        "localField": "EnterpriseNumber",
        "foreignField": "EntityNumber",
        "as": "contacts"
    }},
    {"$lookup": {
        "from": "activity",
        "localField": "EnterpriseNumber",
        "foreignField": "EntityNumber",
        "as": "activities"
    }},
    {"$lookup": {
        "from": "branch",
        "localField": "EnterpriseNumber",
        "foreignField": "EnterpriseNumber",
        "as": "branches"
    }},
    {"$lookup": {
        "from": "establishments_full",
        "localField": "EnterpriseNumber",
        "foreignField": "EnterpriseNumber",
        "as": "establishments"
    }},
    {"$merge": {"into": "entreprises_full", "whenMatched": "replace", "whenNotMatched": "insert"}}
], allowDiskUse=True)

print("  -> entreprises_full créée.")

total = db["entreprises_full"].count_documents({})
print(f"\nTerminé. {total} documents dans 'entreprises_full'.")

sample = db["entreprises_full"].find_one()
print("\nChamps du document final :", list(sample.keys()))