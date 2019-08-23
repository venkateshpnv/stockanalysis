import os
# Excel operations
import xlrd
import csv
import pymongo
import re
import time
import requests

from datetime import date, timedelta, datetime
import numpy as np
import pandas as pd
import pandas_datareader as pdr

import internet
import parse_html
from common import *
from datastructures import *
import conf

j = 0
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

def update_dummy_dcf_numbers(col, stock):
    update_field(col, stock.bscs.symbol, "num.discount_rate", 0)
    update_field(col, stock.bscs.symbol, "num.inflation", 0)
    update_field(col, stock.bscs.symbol, "num.growth_1to5", 0)
    update_field(col, stock.bscs.symbol, "num.growth_6to8", 0)
    update_field(col, stock.bscs.symbol, "num.growth_9to10", 0)
    update_field(col, stock.bscs.symbol, "num.growth_16to20", 0)
    update_field(col, stock.bscs.symbol, "num.eps", 0)
    update_field(col, stock.bscs.symbol, "num.eps_20yr", 0)
    update_field(col, stock.bscs.symbol, "num.fig_yr", 0)
    update_field(col, stock.bscs.symbol, "num.cur_yr", 0)
    update_field(col, stock.bscs.symbol, "num.term_yr", 0)
    update_field(col, stock.bscs.symbol, "num.dcf_price", 0)
    update_field(col, stock.bscs.symbol, "num.dcf_years", 0)
    update_field(col, stock.bscs.symbol, "num.inflated_eps_price", 0)
    update_field(col, stock.bscs.symbol, "num.margin_of_safety", 0)
    update_field(col, stock.bscs.symbol, "num.dcf_return_rate", 0)
    update_field(col, stock.bscs.symbol, "num.cp_return_rate", 0)
    
    update_field(col, stock.bscs.symbol, "fig.price_growth", 0)
    update_field(col, stock.bscs.symbol, "fig.sales_growth", 0)
    update_field(col, stock.bscs.symbol, "fig.profit_growth", 0)
    update_field(col, stock.bscs.symbol, "fig.book_growth", 0)
    update_field(col, stock.bscs.symbol, "fig.cash_growth", 0)
    update_field(col, stock.bscs.symbol, "fig.growth", 0)
    update_field(col, stock.bscs.symbol, "bscs.dcf_calc", "NO")
 
def update_dcf_numbers(col, stock):
    update_field(col, stock.bscs.symbol, "num.discount_rate", stock.num.discount_rate)
    update_field(col, stock.bscs.symbol, "num.inflation", stock.num.inflation)
    update_field(col, stock.bscs.symbol, "num.growth_1to5", stock.num.growth_1to5)
    update_field(col, stock.bscs.symbol, "num.growth_6to8", stock.num.growth_6to8)
    update_field(col, stock.bscs.symbol, "num.growth_9to10", stock.num.growth_9to10)
    update_field(col, stock.bscs.symbol, "num.growth_16to20", stock.num.growth_16to20)
    update_field(col, stock.bscs.symbol, "num.eps", stock.fig.ttm_eps)
    update_field(col, stock.bscs.symbol, "num.eps_20yr", stock.num.eps_20yr)
    update_field(col, stock.bscs.symbol, "num.fig_yr", stock.num.fig_yr)
    update_field(col, stock.bscs.symbol, "num.cur_yr", stock.num.cur_yr)
    update_field(col, stock.bscs.symbol, "num.term_yr", stock.num.term_yr)
    update_field(col, stock.bscs.symbol, "num.dcf_price", stock.num.dcf_price)
    update_field(col, stock.bscs.symbol, "num.dcf_years", stock.num.dcf_years)
    update_field(col, stock.bscs.symbol, "num.inflated_eps_price", stock.num.inflated_eps_price)
    update_field(col, stock.bscs.symbol, "num.margin_of_safety", stock.num.margin_of_safety)
    update_field(col, stock.bscs.symbol, "num.dcf_return_rate", stock.num.dcf_return_rate)
    update_field(col, stock.bscs.symbol, "num.cp_return_rate", stock.num.cp_return_rate)
    
    update_field(col, stock.bscs.symbol, "fig.price_growth", stock.fig.price_growth)
    update_field(col, stock.bscs.symbol, "fig.sales_growth", stock.fig.sales_growth)
    update_field(col, stock.bscs.symbol, "fig.profit_growth", stock.fig.profit_growth)
    update_field(col, stock.bscs.symbol, "fig.book_growth", stock.fig.book_growth)
    update_field(col, stock.bscs.symbol, "fig.cash_growth", stock.fig.cash_growth)
    update_field(col, stock.bscs.symbol, "fig.growth", stock.fig.growth)
    update_field(col, stock.bscs.symbol, "bscs.dcf_calc", "YES")
    

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

def get_stat_params(soup, pattern):
    div=soup.find(text=pattern)
    if div and div.parent and div.parent.parent:
        param=div.parent.parent.find("span")
        if param and param.get_text():
            return str_to_float(param.get_text())
        return None
    return None

def get_ratio_params(soup, pattern):
    div=soup.find(text=pattern)
    if div and div.parent and div.parent.parent:
        td=div.parent.parent.find("td")
        if td and td.find_next('td'):
            return str_to_float(td.find_next('td').get_text())
        return None
    return None

def update_US_all_stk_profile():
    db = open_db('Stocks')
    col = db['US_Stocks']
    i = 0
    for doc in col.find({}):
        #if i > 3444:
        if i > -1: # and not doc['bscs']['price']:
            sym = doc['bscs']['symbol']
            url = 'https://www.barchart.com/stocks/quotes/%s/profile' %(sym)
            html_text=internet.get_webpage(url)
            update_US_stk_profile(html_text, col)
            print("%d: %s" %(i, sym))
        i = i + 1

def update_US_stk_profile(html_text, collection):
    soup=parse_html.get_soup(html_text)
    s=soup.find('title').text
    symbol=re.match("(.*?) ",s).group().rstrip()
    #symbol=re.search('\(([^)]+)',s).group(1)
    print(symbol)

    dt = datetime.now().date().strftime("%d-%m-%Y")
    update_field(collection, symbol, "bscs.date", dt)

    #Market Cap
    pattern=re.compile(r'  Market Capitalization, \$K  ')
    val = get_stat_params(soup, pattern)
    if val:
        val = float(val / 1000)
    else:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.mcap": val}})
    

    #Outstanding Shares
    pattern=re.compile(r'Shares Outstanding, K')
    val = get_stat_params(soup, pattern)
    if val:
        val = int(val * 1000)
    else:
        val = 1
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.outstanding_shares": val}})
    
    val = internet.get_LTP('US', symbol)
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.price": val}})

    #60 month Beta
    pattern=re.compile(r'60-Month Beta')
    val = get_stat_params(soup, pattern)
    if not val:
        val = 1
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.five_yr_beta": val}})

    # Insider Shareholders
    pattern=re.compile(r'% of Insider Shareholders')
    val = get_stat_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.promoter_stake": val}})

    # Institutional shareholders
    pattern=re.compile(r'% of Institutional Shareholders')
    val = get_stat_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.dii_stake": val}})

    # Float
    pattern=re.compile(r'Float, K')
    val = get_stat_params(soup, pattern)
    if val:
        val = int(val) * 1000
    else:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.float": val}})

    # % Float
    pattern=re.compile(r'% Float')
    val = get_stat_params(soup, pattern)
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.float_percent": val}})

    # Interest coverage
    pattern=re.compile(r'Interest Coverage')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.interest_coverage": val}})

    # Forward P/E
    pattern=re.compile(r'Price/Earnings forward')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.forward_PE": val}})

    #TTM PE 
    pattern=re.compile(r'Price/Earnings ttm')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.ttm_PE": val}})

    #ROE 
    pattern=re.compile(r'Return-on-Equity \(After Tax\)')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.ROE": val}})

    #ROA 
    pattern=re.compile(r'Return-on-Assets \(Before Tax\)')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.ROA": val}})

    #Profit Margin
    pattern=re.compile(r'Profit Margin %')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.GPM": val}})

    #Net Margin
    pattern=re.compile(r'Net Margin %')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.NPM": val}})

    #DtoE
    pattern=re.compile(r'Debt/Equity')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.DtoE": val}})

    #Price/Book
    pattern=re.compile(r'Price/Book')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.PtoB": val}})

    #Book Value / Share
    pattern=re.compile(r'Book Value/Share')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Ratios.BOOK": val}})

    #Annual Dividend Yield
    pattern=re.compile(r'Annual Dividend Yield')
    val = get_ratio_params(soup, pattern)
    if not val:
        val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Dividend.yld": val}})

    #Dividend Payout Ratio
    pattern=re.compile(r'Dividend Payout Ratio')
    val = get_stat_params(soup, pattern)
    if not val:
         val = 0
    collection.update({'bscs.symbol': symbol}, {'$set': {"Dividend.payout_ratio": val}})

    # Next Earnings Date
    #pattern=re.compile(r'Next Earnings Date')
    #val = get_ratio_params(soup, pattern)
    #print(val)
    #collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.next_eps_date": val}})

    # Split Date
    pattern=re.compile(r'Most Recent Split')
    split_date=split_year=0
    split_factor=1
    #div=soup.find(text=pattern)
    #if div and div.parent and div.parent.parent:
    #    val = div.parent.parent.find("span")
    #    if val and val.get_text():
    #        val = val.get_text()
    #        val = val.lstrip().rstrip()
    #        split_date = val.split(' ')[2]
    #        split_year = val.split(' ')[2].split('/')[2]
    #        cur_year = int(str(datetime.now().year)[2:4])
    #        if int(split_year) < cur_year:
    #            split_year = str('20' + str(split_year))
    #        else:
    #            split_year = str('19' + str(split_year))
    #        split_factor = int(val.split(' ')[0].split('-')[0])/int(val.split(' ')[0].split('-')[1])
    #        print("split date: %r" %(split_date))
    #        print(split_year)
    #        print(split_factor)
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.split_date": split_date}})
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.split_year": split_year}})
    collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.split_factor": split_factor}})

# Can be obsoleted. Replaced with build_US_all_stock_information()
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
            parse_html.populate_US_stocks(db, root, sorted(files), symbol, stock, industry, 'DEAD')
        #break

def update_db_price_volume(collection, stk):
    collection.update({'bscs.symbol': stk.bscs.symbol}, {'$set': {"bscs.price": stk.bscs.price}})
    collection.update({'bscs.symbol': stk.bscs.symbol}, {'$set': {"bscs.volume": stk.bscs.volume}})
    collection.update({'bscs.symbol': stk.bscs.symbol}, {'$set': {"bscs.mcap": stk.bscs.mcap}})
    collection.update({'bscs.symbol': stk.bscs.outstanding_shares}, {'$set': {"bscs.outstanding_shares": stk.bscs.outstanding_shares}})

def update_all_price_volume_db(country):
    db = open_db('Stocks')
    i=0
    if country == 'US':
        docs = db.US_Stocks.find({},no_cursor_timeout=True).sort([["sno",1]])
        for doc in docs:
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
        docs = db.Indian_Stocks.find({}).sort([["sno",1]])
        for doc in docs:
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

def build_US_Stocks_List(excel_file):
    db = open_db('Stocks')
    j = db.US_Stocks_List.find({}).count()
    #print(excel_file)
    #wb = xlrd.open_workbook(excel_file)
    #sheet = wb.sheet_by_index(0)

    entries = []

    with open(excel_file, "r") as f:
        reader=csv.reader(f)
        next(reader)
        for row in reader:
            #print(row[0], row[1], row[2])
            sym = str(row[0]).replace("^","-").replace("~","").lstrip().rstrip()
            name = str(row[1]).replace("^","-").replace("&#39;", "\'").replace("/", "").replace("?", "").replace("*", "").replace(",","").lstrip().rstrip()
            #obj = db.US_Stocks_List.find({"Name":name})

            s=[]
            s.append(sym)
            if "-" in sym:
                s.append(sym.split("-")[0])
            syms={"$in" : s}
            obj = db.US_Stocks_List.find({"symbol":syms})
            if obj.count() == 0:
                entry = []
                entry.append(sym)
                entry.append(name)
                entry.append(row[5])
                entry.append(row[6])
                entry.append(row[3])
                entry.append(row[2])
                if "." in sym:
                    price_change = internet.price_change('US', sym.split(".")[0], name, 365, 'HOT')
                elif "-" in sym:
                    price_change = internet.price_change('US', sym.split("-")[0], name, 365, 'HOT')
                else:
                    price_change = internet.price_change('US', sym, name, 365, 'HOT')
                if price_change:
                    entry.append(str(round(price_change*100, 2))+'%')
                else:
                    entry.append("-")
                #print(row)
                entries.append(entry)

                j+=1
                stk = {"symbol" : sym, "Name" : name, "Industry" : row[6], "Sector" : row[5], "IPO Year" : row[4], "data" : "NO", "parsed" : "NO", "sno": j}
                db.US_Stocks_List.insert_one(stk)
                #print(stk)
            else:
                #print("%s already present" %(row[0]))
                pass

    return entries
    #for i in range(1,sheet.nrows):
    #    obj = db.US_Stocks_List.find({"symbol":sheet.cell_value(i, 0)})
    #    if obj.count() == 0:
    #        j+=1
    #        stk = {"symbol" : str(sheet.cell_value(i, 0)).lstrip().rstrip(), "Name" : sheet.cell_value(i,1), "Industry" : sheet.cell_value(i, 6), "Sector" : sheet.cell_value(i, 5), "IPO Year" : sheet.cell_value(i, 4), "data" : "NO", "parsed" : "NO", "sno": j}
    #        db.US_Stocks_List.insert_one(stk)
    #    else:
    #        print("%s already present" %(sheet.cell_value(i,0)))

def write_to_file(symbol, filename):
    filename = "/home/vpetla/work/stockanalysis/%s" %(filename)
    f = open(filename, "a")
    symbol=symbol+"\n"
    f.write(symbol)
    f.close()

def get_nin(filename, ninname):
    line=None
    filename = "/home/vpetla/work/stockanalysis/%s" %(filename)
    ninname  = "/home/vpetla/work/stockanalysis/%s" %(ninname)
    f1 = open(filename,"r")
    f2 = open(ninname,"a")

    for line in f1:
        #print(line)
        pass
    if line:
        f2.write(line)
    f2.close()

    # {"$ne": [ "AAP", "BLR", "CLG" ] }
    s=[]
    #f2 = open("/home/vpetla/work/stockanalysis/nins.txt","r")
    f2 = open(filename,"r")
    for line in f2:
        line = line.replace("\n","")
        s.append(line)
    syms = {"$nin" : s}
    nin = {"bscs.symbol":syms}
    #nin = {"$and": [{"fig.EPS_History": {"$exists": False}}, {"fig.DIVIDEND_History": {"$exists": False}},{"fig.Split_History": {"$exists": False}}, {"bscs.symbol":syms}]}
    #print(nin)
    return nin

def build_US_all_EPS_New():
    print("****************** Building US EPS ******************")
    db = open_db('Stocks')
    get_nin("file2.txt", "nins2.txt")
    f1 = open("/home/vpetla/work/stockanalysis/nins.txt", "r")
    f2 = open("/home/vpetla/work/stockanalysis/nins2.txt", "r")
    #for stock in f:
    for i, stock in enumerate(f1):
        if stock in f2:
            print("%s in nins2" %(stock.split("\n")[0]))
            #break
            pass
        else:
            stock = stock.split("\n")[0]
            docs = db.US_Stocks.find({"bscs.symbol":stock})
            if docs.count() == 1:
                for doc in docs:
                    stk = dbObject(**doc)
                    #if stk.bscs.price == 0:
                    print("%d: %s: %s"%(stk.sno,stk.bscs.symbol,stk.bscs.name))
                    write_to_file(stk.bscs.symbol, "file2.txt")
                    internet.populate_US_EPS(stk)
                    #break
    f1.close()
    f2.close()

def build_US_all_EPS():
    print("****************** Building US EPS ******************")
    db = open_db('Stocks')
    #docs = db.US_Stocks.find({"bscs.symbol":"CMCL"}).sort([["sno",1]])
    #docs = db.US_Stocks.find({}).sort([["sno",1]])
    #docs = db.US_Stocks.find({"fig.EPS_History":{"$exists":False}})
    #docs  = db.US_Stocks.find(get_nin("file.txt", "nins.txt"))
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"fig.DIVIDEND_History": {"$exists": False}},{"fig.Split_History": {"$exists": False}}, {"bscs.symbol":{"$ne": "ARR"}}]})
    #docs = db.US_Stocks.find({"fig.EPS_History": {"$exists": False}})
    docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"bscs.symbol":{"$nin": ["DAIO", "IBCP", "MRTN", "SLGN"]}}]},no_cursor_timeout=True)
    count = docs.count()
    print(count)
    if count == 0:
        print("***************** Completed fetching EPS  *************")
        return
    #try:
    for doc in docs:
        sno = doc['sno']
        if sno > 0:
        #if sno > 3000:
        #    break
        #if sno > 664:
            stk = dbObject(**doc)
            #if stk.bscs.price == 0:
            print("%d: %s: %s"%(sno,stk.bscs.symbol,stk.bscs.name))
            write_to_file(stk.bscs.symbol, "file2.txt")
            internet.populate_US_EPS(stk)
            #break
 
def build_US_all_earnings_estimates():

    db = open_db('Stocks')
    #docs = db.US_Stocks.find({"bscs.symbol":"AVGO"}).sort([["sno",1]])
    #docs = db.US_Stocks.find({}).sort([["sno",1]])
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"fig.DIVIDEND_History": {"$exists": False}},{"fig.Split_History": {"$exists": False}}, {"bscs.symbol":{"$ne": "ARR"}}]})
    docs = db.US_Stocks.find({"quart_fig.Earning_Estimates":{"$exists":False}},no_cursor_timeout=True)
    count = docs.count()
    print(count)
    if count == 0:
        print("***************** Completed fetching earnings estimates *************")
        return
    #try:
    for doc in docs:
        sno = doc['sno']
        if sno > 0:
        #if sno > 3000:
        #    break
        #if sno > 664:
            stk = dbObject(**doc)
            #if stk.bscs.price == 0:
            print("%d: %s: %s"%(sno,stk.bscs.symbol,stk.bscs.name))
            internet.populate_US_earnings_estimates(stk)
            #break
    #except Exception as e:
        #PRINT_ERR("Mongo DB exception")
        #PRINT_ERR(str(e))
        #return -1
        #time.sleep(5)
        #num = sno
        #db = open_db('Stocks')
        #docs = db.US_Stocks.find({}).sort([["sno",1]])
        #for doc in docs:
        #    sno = doc['sno']
        #    if sno > 3000:
        #        break
        #    if sno > num-1:
        #    #    break
        #    #if sno > 24:
        #        stk = dbObject(**doc)
        #        #if stk.bscs.price == 0:
        #        print("%d: %s: %s"%(sno,stk.bscs.symbol,stk.bscs.name))
        #        internet.populate_US_earnings_estimates(stk)
        #        #break
 
def build_US_quarterly_stock_information(stk):
    path = internet.get_US_quarterly_stock_page(stk.bscs.symbol, stk.bscs.name)
    for (root,dirs,files) in os.walk(path, topdown=True):
       files = [f for f in files if not f[0] == '.']
       dirs[:] = [d for d in dirs if d not in sheet.cell_value(i,0)]
       dirs[:] = [d for d in dirs if not d[0] == '.']
       #print(root)
       #print(dirs)
       #print(sorted(files))
       parse_html.populate_US_stocks_quarterly(root, sorted(files), stk)

def get_US_Stock_list():
    nasdaq_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
    wb=requests.get(nasdaq_url)
    f=open(conf.nasdaq_stocks,"wb")
    f.write(wb.content)
    f.close()

    nyse_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download"
    wb=requests.get(nyse_url)
    f=open(conf.nyse_stocks,"wb")
    f.write(wb.content)
    f.close()

    amex_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download"
    wb=requests.get(amex_url)
    f=open(conf.amex_stocks,"wb")
    f.write(wb.content)
    f.close()

def build_US_All_Stocks_List():
    get_US_Stock_list()
    new_stocks = [] 
    head=["Symbol", "Name", "Sector", "Industry", "Market Cap", "$Price", "Max Price Change"]
    new_stocks.append(head)
    new_stocks.extend(build_US_Stocks_List(conf.amex_stocks))
    new_stocks.extend(build_US_Stocks_List(conf.nyse_stocks))
    new_stocks.extend(build_US_Stocks_List(conf.nasdaq_stocks))
    # If atleast one new IPO
    if len(new_stocks) > 1:
        s = parse_html.html_table(new_stocks)
        #print(s)
        subject = 'New Stocks :' + str(datetime.now().date())
        internet.send_email2('petlafin@gmail.com', 'Tasche3#Fin', 'petlafin@gmail.com', subject, s)
    return len(new_stocks)

def build_US_stock_information(doc):
    db   = open_db('Stocks')
    sym  = doc['symbol']
    name = doc['Name']

    name = name.replace(",","").lstrip().rstrip()
    if "&#39;" in name:
        print("stk has &")
        name = name.replace("&#39;", "\'")
        db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}})
    if "/" in name:
        print("stk has /")
        name = name.replace("/", "")
        db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}}) 
    if "?" in name:
        print("stk has ?")
        name = name.replace("?", "")
        db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}}) 
    if "*" in name:
        print("stk has *")
        name = name.replace("*", "")
        db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}}) 
    
    if "^" in sym:
        print("symbol has ^")
        sym = sym.replace("^", "-").lstrip().rstrip()
        print(sym)
        db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"symbol": sym}})
    if "~" in sym:
        print("symbol has ~")
        sym = sym.replace("~", "").lstrip().rstrip()
        print(sym)
        db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"symbol": sym}})
    if "?" in sym:
        print("symbol has ?")
        sym = sym.replace("?", "").lstrip().rstrip()
        print(sym)
        db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"symbol": sym}})


    obj = db.US_Stocks.find({"bscs.symbol":sym})
    if obj.count() > 0:
        print("%s: %s: already exists. Skipping" %(sym, name))
        return

    path = internet.get_US_stock_page(sym, name)
    
    ret=True
    for (root,dirs,files) in os.walk(path, topdown=True):
        files = [f for f in files if not f[0] == '.']
        dirs[:] = [d for d in dirs if d not in sheet.cell_value(i,0)]
        dirs[:] = [d for d in dirs if not d[0] == '.']
        #print(root)
        #print(dirs)
        #print(sorted(files))
        if parse_html.populate_US_stocks(db, root, sorted(files), sym, name, doc['Sector'], doc['Industry']) is True:
            db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"data": "YES"}})
        else:
            ret = False
        db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})
   
    if ret is True:
        remove_dir(path)
 
def build_US_all_stock_information():
    db = open_db('Stocks')

    stocks_list = db.US_Stocks_List.find({})
    j=0
    for i, doc in enumerate(stocks_list):
    #for doc in db.US_Stocks_List.find({"symbol":"PLG"}).sort([["sno",1]]):
        sno = doc['sno']
        #if sno > 3443:
        #    break
        if sno > 0:
        #if sno > 5896:
        #if sno > 2134:
            name = doc['Name']
            #if name.find("Fund") != -1 or name.find("Trust") != -1:
            #    print("Skipping: %r" %(name))
            #    db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})
            #    continue

        #if i > -1:
            obj = db.US_Stocks.find({"bscs.symbol":doc['symbol']})
            if obj.count() == 0:
            #if doc['parsed'] != 'YES' and obj.count() == 0:
                print("%d: %s: %s "%(sno,doc['symbol'], doc['Name']))
                build_US_stock_information(doc)
                #j += 1
                #update_field(db.US_Stocks, doc['symbol'], "sno", j)
            else:
                #print("%d: %s: %s already present, skipping" %(sno,doc['symbol'], doc['Name']))
                pass
            #name = stock['Name']
            #sym = stock['symbol']
            #name = name.replace("&#39;", "\'")
            #name = name.replace("/", "")
            #sym = sym.replace("^", "-")
            #db.US_Stocks_List.update({"symbol":stock['symbol']},{'$set':{"Name":name}})
            #db.US_Stocks_List.update({'symbol': stock['symbol']}, {'$set': {"symbol": sym}})


    set_sno('US')
    # Create index based on sno
    db.US_Stocks.createIndex({sno: -1})
    db.US_Stocks.createIndex({ "$**": "text" },{ name: "TextIndex" })

    print("Total : %d" %(j))


#Update sector and industry info in the database for each stock from the US_List database
def update_sector_info():
    db = open_db('Stocks')

    stocks_list = db.US_Stocks.find({},no_cursor_timeout=True)
    j=0
    for i, doc in enumerate(stocks_list):
        if i > -1:
            obj = db.US_Stocks_List.find({"symbol":doc['bscs']['symbol']})
            if obj.count() == 1:
                db.US_Stocks.update({'bscs.symbol': obj[0]['symbol']}, {'$set': {"bscs.sector": obj[0]['Sector']}})
                db.US_Stocks.update({'bscs.symbol': obj[0]['symbol']}, {'$set': {"bscs.industry": obj[0]['Industry']}})
                j += 1
    print("Total : %d" %(j))

def get_beta(sym, bindex, sdate, edate):
    betas = {}
    sym = sym.replace('.', '-')
    try:
        df = pdr.DataReader(sym,'yahoo',sdate,edate)
    except KeyError:
        return None

    dfb = pdr.DataReader(bindex,'yahoo',sdate,edate)
   
    # Calculate CAGR
    first = df['Adj Close'][0]
    if isinstance(first, complex):
        print("first is complex number")
    last = df['Adj Close'][-1]
    if isinstance(last, complex):
        print("last is complex number")
    #print(df['Adj Close'].head(5))
    #print(df['Adj Close'].tail(5))
    years = (edate-sdate).days/365
    #print("sdate: %r, edate: %r, last: %r, first: %r"%(sdate, edate, last, first))
    try:
        cagr = round((((last/first)**(1/years))-1), 4)
    except Exception as e:
        print(str(e))
        return
    first = dfb['Adj Close'][0]
    last = dfb['Adj Close'][-1]
    b_cagr = round((((last/first)**(1/years))-1), 4)
    first = dfb['Adj Close'][0]
    #print("Years: %r, first: %r, last: %r, cagr: %r, cagr_b: %r" %(round(years,2), first, last, round(cagr,4), round(b_cagr,4)))

    # create a time-series of monthly data points
    time_period=12. #months
    rts = df.resample('M').last()
    rbts = dfb.resample('M').last()
    dfsm = pd.DataFrame({'s_adjclose' : rts['Adj Close'],
                            'b_adjclose' : rbts['Adj Close']},
                            index=rts.index)
    
    # compute returns
    dfsm[['s_returns','b_returns']] = dfsm[['s_adjclose','b_adjclose']]/\
        dfsm[['s_adjclose','b_adjclose']].shift(1) -1
    dfsm = dfsm.dropna()
    covmat = np.cov(dfsm["s_returns"],dfsm["b_returns"])
    
    # calculate measures now
    beta = covmat[0,1]/covmat[1,1]
    alpha= np.mean(dfsm["s_returns"])-beta*np.mean(dfsm["b_returns"])
    #alpha_pure= np.mean(dfsm["s_returns"])-np.mean(dfsm["b_returns"])
    #print("alpha: %r" %(alpha))
    #print("alpha: %r" %(alpha_pure))

    ypred = alpha + beta * dfsm["b_returns"]
    SS_res = np.sum(np.power(ypred-dfsm["s_returns"],2))
    SS_tot = covmat[0,0]*(len(dfsm)-1) # SS_tot is sample_variance*(n-1)
    r_squared = 1. - SS_res/SS_tot

    # 5- year volatiity and 1-year momentum
    volatility = np.sqrt(covmat[0,0])
    #momentum = np.prod(1+dfsm["s_returns"].tail(12).values) -1
    
    # annualize the numbers
    prd = 12. # used monthly returns; 12 periods to annualize
    #alpha = alpha*prd
    alpha = alpha*time_period
    #alpha_pure = alpha_pure*time_period
    alpha_pure = round(cagr - b_cagr, 4)
    #print("alpha/year: %r" %(alpha))
    #print("alpha_pure/year: %r" %(alpha_pure))
    volatility = volatility*np.sqrt(time_period)

    betas.update({"Index_CAGR":b_cagr})
    betas.update({"CAGR":cagr})
    betas.update({"beta":beta})
    betas.update({"alpha":alpha})
    betas.update({"alpha_pure":alpha_pure})
    betas.update({"r_squared":r_squared})
    betas.update({"volatility":volatility})
    #print(betas)
    return betas
    #print (stock, beta, alpha, r_squared, volatility, momentum)
    
def update_stock_recession_beta(db, sym):
    years = recessions.keys()
    for year in years:
        st_date = datetime.strptime(recessions[year]['start'], "%B %Y").date()
        en_date = datetime.strptime(recessions[year]['end'], "%B %Y").date()
        #print(st_date)
        #print(en_date)
        betas = get_beta(sym, '^GSPC', st_date, en_date)
        if betas:
            field="fig.betas.recession.%s" %(year)
            db.update({'bscs.symbol':sym},{'$set': {field : betas}})
    return


def update_stock_betas():
    db_handle = open_db('Stocks')
    db = db_handle.US_Stocks
    bindex='^GSPC'
    docs = db.find({ "$and": [{"$or": [{"fig.betas.recession": {"$exists": False}},{"fig.betas.since_last_recession": {"$exists": False}}, {"fig.betas.whole": {"$exists": False}}, {"fig.betas.five_year": {"$exists": False}}, {"fig.betas.one_year": {"$exists": False}}, {"fig.betas.six_months": {"$exists": False}}]}, {"bscs.symbol":{"$nin" : ["AAN", "GOLF"]}}]}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({"fig.betas": {"$exists": False}},no_cursor_timeout=True).sort([["sno",1]])
    print(docs.count())
    for i, doc in enumerate(docs):
        sym = doc['bscs']['symbol']
        print("%r: %r" %(doc['sno'], sym))
        update_stock_recession_beta(db, sym)
        since = doc['bscs']['since']
        since_start = datetime.strptime(since, "%Y-%m-%d").date()

        #Since last recession
        betas = None
        year = sorted(recessions.keys())[-1]
        st_date = datetime.strptime(recessions[year]['start'], "%B %Y").date()
        en_date = datetime.now().date()
        if (st_date - since_start).days > 0:
            betas = get_beta(sym, bindex, st_date, en_date)
        if betas:
            field="fig.betas.since_last_recession"
            db.update({'bscs.symbol':sym},{'$set': {field : betas}})

        #whole beta
        st_date = since_start
        en_date = datetime.now().date()
        betas = get_beta(sym, bindex, st_date, en_date)
        if betas:
            field="fig.betas.whole"
            db.update({'bscs.symbol':sym},{'$set': {field : betas}})

        #5 year beta
        en_date = datetime.now().date()
        betas = None
        if (en_date - st_date).days >= 5*365:
            st_date = en_date - timedelta(days=5*365)
            betas = get_beta(sym, bindex, st_date, en_date)
        if betas:
            field="fig.betas.five_year"
            db.update({'bscs.symbol':sym},{'$set': {field : betas}})

        #1 year beta
        st_date = since_start
        en_date = datetime.now().date()
        betas = None
        if (en_date - st_date).days >= 1*365:
            st_date = en_date - timedelta(days=1*365)
            betas = get_beta(sym, bindex, st_date, en_date)
        if betas:
            field="fig.betas.one_year"
            db.update({'bscs.symbol':sym},{'$set': {field : betas}})

        #6 months beta
        st_date = since_start
        en_date = datetime.now().date()
        betas = None
        if (en_date - st_date).days >= 365/2:
            st_date = en_date - timedelta(days=365/2)
            betas = get_beta(sym, bindex, st_date, en_date)
        if betas:
            field="fig.betas.six_months"
            db.update({'bscs.symbol':sym},{'$set': {field : betas}})

def set_sno(country):
    db = open_db('Stocks')
    if country == 'US':
        col = db['US_Stocks']
    elif country == 'India':
        col = db['Indian_Stocks']
    else:
        return

    i = 1
    for doc in col.find({}).sort([["_id",1]]):
        update_field(col, doc['bscs']['symbol'], "sno", i)

        i += 1
