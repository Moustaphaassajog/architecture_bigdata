from pymongo import MongoClient

MONGO_URI = "mongodb://admin:motdepasse@mongodb:27017/"
DB_NAME = "kbo_db"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

silver_coll = db["enterprise_silver"]
gold_coll = db["hotel_gold"]