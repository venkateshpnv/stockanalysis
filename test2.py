#!/bin/python3
import DB

items = DB.get_symbols_names_from_mongo()
print(items)
