from pymongo import MongoClient
import credentials as cred

host=cred.mongo_host
port=cred.mongo_port
user=cred.mongo_user
password=cred.mongo_pass
protocol="mongodb"

client = MongoClient(f"{protocol}://{user}:{password}@{host}:{port}")
db = client.contracts
eu = db.eu
cpv_div_all_data = db.cpv_divisions_all_data
countries_all_data = db.countries_all_data
contracts_value_euro = db.contracts_value_euro
companies_all_data = db.companies_all_data