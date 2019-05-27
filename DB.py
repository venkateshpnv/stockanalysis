import os
# Excel operations
import xlrd
import pymongo
import re
from datetime import datetime

import internet
import parse_html
from common import *
import conf

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
    symbol=re.search('\(([^)]+)',s).group(1)
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
    collection.update({'bscs.symbol': stk.bscs.shares_outstanding}, {'$set': {"bscs.outstanding_shares": stk.bscs.shares_outstanding}})

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

def build_US_Stocks_List(excel_file):
    db = open_db('Stocks')
    print(excel_file)
    wb = xlrd.open_workbook(excel_file)
    sheet = wb.sheet_by_index(0)
    for i in range(1,sheet.nrows):
        obj = db.US_Stocks_List.find({"symbol":sheet.cell_value(i, 0)})
        if obj.count() == 0:
            stk = {"symbol" : sheet.cell_value(i, 0), "Name" : sheet.cell_value(i,1), "Industry" : sheet.cell_value(i, 6), "Sector" : sheet.cell_value(i, 5), "IPO Year" : sheet.cell_value(i, 4), "data" : "NO", "parsed" : "NO"}
            db.US_Stocks_List.insert_one(stk)
        else:
            print("%s already present" %(sheet.cell_value(i,0)))

def build_US_All_Stocks_List():
    build_US_Stocks_List(conf.amex_stocks)
    build_US_Stocks_List(conf.nyse_stocks)
    build_US_Stocks_List(conf.nasdaq_stocks)

def build_US_stock_information(doc):
    db   = open_db('Stocks')
    sym  = doc['symbol']
    name = doc['Name']
    if "&#39;" in name:
        print("stk has &")
        name = name.replace("&#39;", "\'")
        db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}})
    if "/" in name:
        print("stk has /")
        name = name.replace("/", "")
        db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}}) 
    if "^" in sym:
        print("symbol has ^")
        sym = sym.replace("^", "-")
        print(sym)
        db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"symbol": sym}})
    
    path = internet.get_US_stock_page(sym, name)
    
    for (root,dirs,files) in os.walk(path, topdown=True):
        files = [f for f in files if not f[0] == '.']
        dirs[:] = [d for d in dirs if d not in sheet.cell_value(i,0)]
        dirs[:] = [d for d in dirs if not d[0] == '.']
        #print(root)
        #print(dirs)
        #print(sorted(files))
        if parse_html.populate_US_stocks(db, root, sorted(files), sym, name, doc['Sector'], doc['Industry']) is True:
            db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"data": "YES"}})
        db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})
    
    remove_dir(path)
 
def build_US_all_stock_information():
    db = open_db('Stocks')

    stocks_list = db.US_Stocks_List.find({})
    j=0
    for i, doc in enumerate(stocks_list):
        if i > -1:
            obj = db.US_Stocks.find({"bscs.symbol":doc['symbol']})
            if obj.count() == 0:
            #if doc['parsed'] != 'YES' and obj.count() == 0:
                print("%d: %s: %s "%(i,doc['symbol'], doc['Name']))
                build_US_stock_information(doc)
                j += 1
            else:
                db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"data": "YES"}})
                db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})
            #name = stock['Name']
            #sym = stock['symbol']
            #name = name.replace("&#39;", "\'")
            #name = name.replace("/", "")
            #sym = sym.replace("^", "-")
            #db.US_Stocks_List.update({"symbol":stock['symbol']},{'$set':{"Name":name}})
            #db.US_Stocks_List.update({'symbol': stock['symbol']}, {'$set': {"symbol": sym}})

    print("Total : %d" %(j))


#Update sector and industry info in the database for each stock from the US_List database
def update_sector_info():
    db = open_db('Stocks')

    stocks_list = db.US_Stocks.find({})
    j=0
    for i, doc in enumerate(stocks_list):
        if i > -1:
            obj = db.US_Stocks_List.find({"symbol":doc['bscs']['symbol']})
            if obj.count() == 1:
                db.US_Stocks.update({'bscs.symbol': obj[0]['symbol']}, {'$set': {"bscs.sector": obj[0]['Sector']}})
                db.US_Stocks.update({'bscs.symbol': obj[0]['symbol']}, {'$set': {"bscs.industry": obj[0]['Industry']}})
                j += 1
    print("Total : %d" %(j))

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
