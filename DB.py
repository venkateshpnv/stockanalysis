import os
# Excel operations
import xlrd
import pymongo

import internet
import parse_html
from common import *

class dbObject:
    def __init__(self, **obj):
        for k,v in obj.items():
            if isinstance(v,dict):
                self.__dict__[k] = dbObject(**v)
            else:
                self.__dict__[k] = v

########################### DB Related Calls ########3###################
def open_db(db_name):
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client[db_name]
    return db

def update_field(col, symbol, field, value):
    col.update({"bscs.symbol":symbol},{'$set':{field:value}})
 
def write_to_collection(col, doc):
    if col.find({"bscs.symbol":doc['bscs']['symbol']}).count() > 0 :
        print("Stock exists")
        return
    col.insert_one(doc)
    print("Count: %r" %(col.count()))
    #x = col.find_one()
    #print(x)

# Fetches symbol name from BSE_Stocks.xls file
# for BSE symbol and updates the "sample" collection
# Test API. Not used often
def update_db_symbol_id():
    db = open_db('Stocks')
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
    for i in range(1,2):
    #for i in range(1,sheet.nrows):
        print("%r: %s : %s" %(i, str(int(sheet.cell_value(i, 0))), sheet.cell_value(i,1)))
        sym = str(int(sheet.cell_value(i, 0)))
        sym_id = sheet.cell_value(i, 1)
        collection = db['sample']
        sym="505075"
        collection.update({"bscs.bse_symbol": sym},
                {"$set": {"bscs.symbol": sym_id}})

# Populates all html file names in a file
def build_files(files):
    f = open("files.txt", "w")
    for stock in files:
        f.write(stock)
        f.write("\n")
    f.close()

def build_India_database(files, data_type):
    db = open_db('Stocks')
    #db.Indian_Stocks.drop()
    f = open("India_Stocks/files.txt", "r")

    for i, stock_page in enumerate(f):
        if i > -1:

            print("%d: %s" %(i, stock_page))
            stock = parse_html.get_India_stock_info(stock_page.replace("\n",""))
            if not stock:
                PRINT_ERR("Unable to get stock info of %s" %(stock_page))
                continue
            if data_type == 'HOT':
                val = internet.get_LTP('India', stock.bscs.symbol)
                if val == -1:
                    PRINT_ERR("Unable to get LTP for %s"%(stock.bscs.name))
                else:
                    stock.bscs.price = val

            print(stock.bscs)
            obj = build_json_object(stock)
            #write_to_collection(db['Indian_Stocks'], obj)
            stock = None
            obj   = None

def build_US_database():
    db = open_db('Stocks')
    #db.US_Stocks.drop()
    wb = xlrd.open_workbook('US_Stocks/US_Stocks.xls')
    sheet = wb.sheet_by_index(0)
    for i in range(1,sheet.nrows):
        stock = sheet.cell_value(i, 0)
        stock = stock.split('/')[2]
        objs = db.US_Stocks_List.find({"Name":stock})
        for obj in objs:
            symbol = obj['symbol']
            industry = obj['Industry']
        for (root,dirs,files) in os.walk(sheet.cell_value(i,0), topdown=True):
            files = [f for f in files if not f[0] == '.']
            dirs[:] = [d for d in dirs if d not in sheet.cell_value(i,0)]
            dirs[:] = [d for d in dirs if not d[0] == '.']
            #print(root)
            #print(dirs)
            #print(sorted(files))
            print("%d: %s" %(i, root))
            parse_html.populate_US_stocks(db, root, sorted(files), symbol, stock, industry)
        #break

def update_db_price_volume(collection, stk):
    collection.update({'bscs.symbol': stk.bscs.symbol}, {'$set': {"bscs.price": stk.bscs.price}})
    collection.update({'bscs.symbol': stk.bscs.symbol}, {'$set': {"bscs.volume": stk.bscs.volume}})
    collection.update({'bscs.symbol': stk.bscs.symbol}, {'$set': {"bscs.mcap": stk.bscs.mcap}})
    collection.update({'bscs.symbol': stk.bscs.shares_outstanding}, {'$set': {"bscs.shares_outstanding": stk.bscs.shares_outstanding}})

def update_all_price_volume_db(country):
    db = open_db('Stocks')
    i=0
    if country == 'US':
        for doc in db.US_Stocks.find():
            if i > -1:
                stk = dbObject(**doc)
                #if stk.bscs.price == 0:
                print("%d: %s: %s"%(i,stk.bscs.symbol,stk.bscs.name))
                stk = internet.get_price_volume(stk, country)
                if stk:
                    update_db_price_volume(db.US_Stocks, stk)
            i+=1
            #break
    elif country == 'India':
        for doc in db.Indian_Stocks.find():
            if i > -1:
                stk = dbObject(**doc)
                #if stk.bscs.price == 0:
                print("%d: %s: %s"%(i,stk.bscs.symbol,stk.bscs.name))
                stk = internet.get_price_volume(stk, country)
                if stk:
                    update_db_price_volume(db.Indian_Stocks, stk)
            i+=1
            #break
    else:
        PRINT_ERR("Unknown Country")

#Find missing entries in the db.
# Compare with entries in BSE_Stocks.xls
def find_files():
    db = open_db('Stocks')
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    f = open("missing_files.txt", "w")
    for i in range(1,sheet.nrows):
        obj = db.Indian_Stocks.find({"bscs.symbol":sheet.cell_value(i, 1)})
        if obj.count() == 0:
            print("%s Not found"%(sheet.cell_value(i, 2)))
            f.write(sheet.cell_value(i, 2))
            f.write("\n")

    f.close()

def build_US_Stocks_List():
    db = open_db('Stocks')
    wb = xlrd.open_workbook(amex_stocks)
    sheet = wb.sheet_by_index(0)
    for i in range(1,sheet.nrows):
        obj = db.US_Stocks_List.find({"symbol":sheet.cell_value(i, 0)})
        if obj.count() == 0:
            stk = {"symbol": sheet.cell_value(i, 0), "Name": sheet.cell_value(i,1), "Industry": sheet.cell_value(i, 6)}
            db.US_Stocks_List.insert_one(stk)
        else:
            print("%s already present" %(sheet.cell_value(i,0)))


