import sys
import os
import sys
# Excel operations
import xlrd
import csv
import pymongo
import re
import time
import requests
import math
from math import nan, isnan

from datetime import date, timedelta, datetime as dt
from dateutil.relativedelta import relativedelta
import datetime
import numpy as np
import pandas as pd
import pandas_datareader as pdr

import internet
import parse_html
from common import *
from datastructures import *
import conf
import hdf5

import sqlalchemy
from sqlalchemy import MetaData, Table, DDL, Column, Integer, Float, String, select, column
from sqlalchemy.orm import sessionmaker
#from sqlalchemy import *
#metadata=MetaData()
#table = Table('table_name', metadata, autoload=True, autoload_with=sql_engine)
#new_col = Column('new_col', Integer)
#table.append_column(new_col)
#Working code
#query = DDL('ALTER TABLE sample_table ADD column new_col Integer')
#sql = DDL('update sample_table set id=20, marks=30 where name=\'myname2\''
#sql_engine.execute(query)

#Session = sessionmaker(bind=test_engine)
#session= Session()


import threading
import multiprocessing
import copy

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement, BatchStatement
from cassandra import ConsistencyLevel

thread_factor=4

def open_sql_connection(ip, user, passwd, port=3036, db=None):
    connection_string="mysql+pymysql://"+user+":"+passwd+"@"+ip+":"+str(port)
    mysql_engine = None
    if db:
        connection_string = connection_string + "/" + db
    max_threads = multiprocessing.cpu_count() * thread_factor
    try:
        mysql_engine = sqlalchemy.create_engine("mysql+pymysql://root:petla123@localhost:3306/US_Stocks", pool_size=max_threads*4)
    #return sqlalchemy.create_engine(connection_string, pool_size=max_threads)
    #return sqlalchemy.create_engine("mysql+pymysql://vpetla:petla123@localhost:3306/Stocks", pool_size=max_threads)
    except Exception as E:
        print("%r" %(str(E)))
        sys.exit(1)
    return mysql_engine

def close_sql_connection(mysql_engine):
    mysql_engine.dispose()

# This function is to fix the issue with the YahooFinance.
# Sometimes, it returns wrong volume information for the present date.
# Especially for the indices.
def check_volume_of_last_record(mysql_engine, table_name):
    query = 'select Volume from {} order by Date desc limit 1'.format(table_name)
    df = pd.read_sql_query(query, mysql_engine)
    if not df.empty and df.iloc[0]['Volume'] == 0:
            PRINT_ERR("Volume is zero for %s. Deleting last row" %(table_name))
            query = 'delete from {} order by Date desc limit 1'.format(table_name)
            mysql_engine.execute(query)

def mysql_get_price(sql_engine, table_name, req_date, from_date):
    query = 'select `Date`, `Adj Close` from {} where Date = (select max(Date) from {} where Date  <= \'{}\')'.format(table_name, table_name, req_date)
    df1 = pd.read_sql_query(query, sql_engine)

    query = 'select `Date`, `Adj Close` from {} where Date = (select min(Date) from {} where Date  >= \'{}\')'.format(table_name, table_name, req_date)
    df2 = pd.read_sql_query(query, sql_engine)

    if df1.empty and df2. empty:
        return 0
    if df1.empty:
        return df2['Adj Close'][0]
    if df2.empty:
        return df1['Adj Close'][0]
    
    cur = dt.strptime(req_date, "%Y-%m-%d").date()
    date1 = pd.to_datetime(df1['Date'][0]).date()
    date2 = pd.to_datetime(df2['Date'][0]).date()
  
    # Both are same, return either
    if date1 == date2:
        return df1['Adj Close'][0]

    # required should never be from date
    if from_date == str(date1):
        return df2['Adj Close'][0]
    if from_date == str(date2):
        return df1['Adj Close'][0]

    if abs(cur-date1) < abs(cur-date2):
        return df1['Adj Close'][0]

    return df2['Adj Close'][0]

def mysql_get_latest_price(sql_engine, country, sym):
    table_name = get_symbol_table_name(sym)
    query = 'select Date, `Adj Close` from {} order by Date desc limit 1'.format(table_name)
    df = read_from_sql(query, sql_engine)
    if not df.empty:
        return df['Adj Close'][-1]
    return None


def read_from_sql(query, mysql_engine):
    df = pd.read_sql_query(query, mysql_engine)
    if not df.empty:
        df.index = pd.to_datetime(df['Date'])
    return df

def read_from_sql2(mysql_engine, table_name, columns=None, order='asc', limit=-1):
    metadata = MetaData()
    table = Table(table_name, metadata, autoload=True, autoload_with=mysql_engine)
    conn = mysql_engine.connect()
    table_cols = table.c.keys()

    # stmt=select([column('Adj Close'), column('Date')]).select_from(table).order_by(table.columns.Date.desc()).limit(1)
    if not columns:
        columns = table_cols
    else:
        for c in columns:
            if c not in table_cols:
                print("%s not in %s. Ignoring it" %(c, table_name))
                del columns[columns.index(c)]
    select_cols = []
    for c in columns:
        select_cols.append(column(c))

    stmt = select(select_cols).select_from(table)

    #stmt = select([table])
    if order == 'desc': # default ascending
        stmt = stmt.order_by(table.columns.Date.desc())
    if limit > 0:
        stmt = stmt.limit(limit)

    #stmt = select([table]).where(table.columns.column_name == columns)
    records = conn.execute(stmt).fetchall()
    df=pd.DataFrame(records, columns=columns)
    df.index=df['Date']

    del conn
    del metadata
    del table
    del stmt
    #print(df)
    return df

def write_to_sql(mysql_engine, table, df):
    try:
        df.to_sql(name=table,con=mysql_engine,index=False,if_exists='append')
    except Exception as E:
        print("DB.py: write_to_sql(), table: %r, exception: %r" %(table, str(E)))

def mysql_exists_table(mysql_engine, table_name):
    query = 'show tables like %r;' %(table_name)
    output= mysql_engine.execute(query)
    #If table does not exist
    if output.first() is None:
        return False
    return True

def mysql_check_n_create_table(mysql_engine, table_name):
    if not mysql_exists_table(mysql_engine, table_name):
        print("Creating table: %r" %(table_name))
        query = 'create table '+ table_name + ' like test2;'
        mysql_engine.execute(query)
        #query = 'alter table ' + table +' add index(Date);'
        #mysql_engine.execute(query)

def mysql_get_columns(table):
    c = [i[0] for i in table.columns.items()]
    return c

def mysql_add_column(mysql_engine, table_name, col_name, col_dtype):
    query = 'alter table %s add column %s %s' %(table_name, col, col_dtype)
    mysql_engine.execute(query)

def mysql_add_columns(mysql_engine, table_name, missing_cols):
    unknown_fields = 0
    for c in missing_cols:
        if c in price_fields:
            c_dtype = price_fields_datatypes[price_fields.index(c)]
            mysql_add_column(mysql_engine, table_name, c, c_dtype)
        elif c in price_change_fields:
            c_dtype = price_change_fields_datatypes[price_change_fields.index(c)]
            mysql_add_column(mysql_engine, table_name, c, c_dtype)
        elif c in fin_year_fields:
            c_dtype = fin_year_fields_datatypes[fin_year_fields.index(c)]
            mysql_add_column(mysql_engine, table_name, c, c_dtype)
        elif c in fin_quarter_fields:
            c_dtype = fin_quarter_fields_datatypes[fin_quarter_fields.index(c)]
            mysql_add_column(mysql_engine, table_name, c, c_dtype)
        else:
            unknown_fields = unknown_fields + 1
    return unknown_fields

def mysql_update_table(mysql_engine, table_name, df, check=False, insert=False):
    if df.empty:
        return
    if 'Date.1' in list(df.columns):
        df['Date']=df['Date.1']
        del df['Date.1']
    else:
        df['Date'] = df.index

    try:
        metadata = MetaData()
        table = Table(table_name, metadata, autoload=True, autoload_with=mysql_engine)
        if check:
            mysql_check_n_create_table(mysql_engine, table_name)
            table_cols = mysql_get_columns(table)
            df_cols = list(df.columns)
            missing_cols = list(set(df_cols)-set(table_cols))
            if len(missing_cols) > 0:
                miss = mysql_add_columns(mysql_engine, table_name, missing_cols)
                if miss > 0:
                    PRINT_ERR("Failed to add %r columns to table %r" %(miss, table_name))
                    PRINT_ERR("Columns: ",missing_cols)
                    sys.exit(1)

        conn  = mysql_engine.connect()
        for index, d in df.iterrows():
            items = {}
            key = str(pd.to_datetime(index).date())
            for k in d.keys().to_list(): #Skip date, date.1
                #if k != 'Date':
                items[k]=d[k]
                # TODO: Handle on conflict
            if insert:
                stmt=table.insert().values(items)
            else:
                stmt=table.update().where(table.c.Date==key).values(items)
            conn.execute(stmt)
    finally:
        del metadata
        conn.close()

def check_n_write_to_sql(engine, table, df, fields=None):
    #df['Date'] = df.index.strftime("%Y-%m-%d")
    #df.index = df['Date'] #Is this required? Anyway index will be truncated by sql
    #cols=df.columns.to_list()
    #cols=cols[-1:]+cols[:-1]
    #df=df[cols]
    #query = 'SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = %r AND TABLE_NAME = %r;' %('US_Stocks', 'test2')
    #output= engine.execute(query)
    #cols=output.fetchall()
    #fields=[]
    #for f in cols:
    #   fields.append(f[0])
    #fields = ['Date', 'High', 'Low', 'Open', 'Close', 'Volume', 'Adj Close', 'Day Change', 'Week Change', 'Month Change', 'Quarter Change', 'Half Year Change', 'Year Change', 'Five Year Change', 'Ten Year Change', 'Whole Change']
    #df = df[fields]

    query = 'show tables like %r;' %(table)
    output= engine.execute(query)
    #If table does not exist
    if output.first() is None:
        query = 'create table '+ table + ' like test2;'
        engine.execute(query)
        #query = 'alter table ' + table +' add index(Date);'
        #engine.execute(query)

    # Temporarily stopping this acitivity. Assume test2 has all cols
    ## Add missing columns
    #metadata = MetaData()
    #table_info=Table(table, metadata, autoload=True, autoload_with=engine)
    #table_cols = table_info.columns.keys()
    #df_cols = list(df.columns)
    #miss_cols = list(set(df_cols) - set(cols))
    #for c in miss_cols:
    #    if c in price_fields:
    #        c_dtype = price_fields_datatypes.index(c)
    #        query = 'alter table %s add column %s %s' %(table, c, c_dtype)


    query = 'select * from '+ table
    #query = 'select * from '+ table + ' where Symbol=%r' %(table)
    rdf = pd.read_sql_query(query, engine)
    if not rdf.empty:
        rdf.index = rdf['Date'] #Is this required?
        #Select all rows except that in SQL Database
        df = df[~df.Date.isin(rdf.Date)]
    if not df.empty:
        df.to_sql(name=table, con=engine,index=False,chunksize=1000,if_exists='append')
        #df.to_sql(name=table, con=engine,index=False,if_exists='append')

def get_symbol_table_name(symbol):
    if symbol in India_indices.keys():
        symbol = India_indices[symbol]
    elif symbol in US_indices.keys():
        symbol = US_indices[symbol]
    return 'STK'+symbol.replace('.','_')

def get_symbols_from_mongo(collection):
    symbols=collection.distinct("bscs.symbol")
    return sorted(symbols)

def rename_table(engine, t):
    new_t = 'STK'+t
    query = 'show tables like %r;' %(new_t)
    output= engine.execute(query)
    #If table does not exist
    if output.first() is not None:
        query = "drop table {}".format(new_t)
        engine.execute(query)
    query = "rename table {} to {}".format(t, new_t)
    engine.execute(query)

def get_symbols_from_sql(country, engine):
    inspector = sqlalchemy.inspect(engine)

    if country == 'India':
        database = 'India_Stocks'
    else:
        database = 'US_Stocks'

    tables = inspector.get_table_names(schema='US_Stocks')
    tables = sorted(tables)
    try:
        del tables[tables.index('test2')]
    except Exception as E:
        pass

    for t in tables:
        if not t.startswith('STK'):
            print("Renaming table: %r" %(t))
            rename_table(engine, t)

    symbols = [t.split('STK')[-1].replace('_', '.')  for t in tables]
    return sorted(symbols)

    #query='select distinct Symbol from ' + table
    #rdf=pd.read_sql_query(query, engine)
    #if not rdf.empty:
    #    symbols = list(rdf['Symbol'])
    #return symbols


j = 0
class dbObject:
    def __init__(self, **obj):
        for k,v in obj.items():
            if isinstance(v,dict):
                self.__dict__[k] = dbObject(**v)
            else:
                self.__dict__[k] = v

def clear_dict(d):
    for k,v in d.items():
        if isinstance(v,dict):
            d[k] = clear_dict(v)
        else:
            if d[k] is None:
                print("%r is None, setting to 0" %(k))
                d[k]=0
    return d

########################## Cassandra Calls #############################
def open_cassandra_cluster(ip, p=None):
    if p:
        return Cluster(contact_points=ip,port=p)
    else:
        return Cluster(contact_points=ip)

def close_cassandra_cluster(cluster):
    cluster.shutdown()

# ip parameter is the list of ips.
# If there is only one ip, still send it as a list
def get_cassandra_session(cluster):
    return cluster.connect()

#########################################################################

client=None
########################### DB Related Calls ########3###################
def open_db(db_name):
    global client
    client = pymongo.MongoClient("mongodb://localhost:27017/", multiprocessing.cpu_count() * thread_factor)
    #print("Opening: %r" %(client))
    db = client[db_name]
    return db

def open_db_client():
    c = pymongo.MongoClient("mongodb://localhost:27017/", multiprocessing.cpu_count() * thread_factor)
    return c 

def close_db():
    global client
    #print("Closing: %r" %(client))
    client.close()

def close_db_client(c):
    c.close()

def ignore_stock(stk):
    #if 'trading' in stk['bscs'].keys():
    #    if stk['bscs']['trading'] == 'NO' or stk['bscs']['trading'] == 'No':
    #        return True
    if 'ignore' in stk.keys():
        if stk['ignore'] == 'YES' or stk['ignore'] == 'Yes':
            return True
    return False

def update_field(col, symbol, field, value):
    col.update({"bscs.symbol":symbol},{'$set':{field:value}})

def get_collection(country, db):
    if country == 'US':
        return db.US_Stocks
    return db.Indian_Stocks

def write_to_collection(col, doc):
    if col.find({"bscs.symbol":doc['bscs']['symbol']}).count() > 0 :
        print("Stock exists")
        return
    col.insert_one(doc)
    print("Count: %r" %(col.count()))
    #x = col.find_one()
    #print(x)

def get_stock_from_db(country, sym):
    c = open_db_client()
    db = c['Stocks']
    if country == 'US':
        col = db.US_Stocks
    else:
        col = db.Indian_Stocks
    stk = col.find({'bscs.symbol':sym})
    close_db_client(c)
    return stk[0]
 
def update_since_dataframe(country, collection, stk):
    #df = hdf5.get_dataframe(country, stk['bscs']['symbol'])
    df = hdf5.read_from_hdf(country, stk['bscs']['symbol'])
    if not df.empty:
        stk['bscs']['since'] = str(df.index[0].date())
        update_field(collection, stk['bscs']['symbol'], 'bscs.since', stk['bscs']['since'])
    else:
        stk['bscs']['since']=""
    return stk

def get_since(country, symbol):
    stk = get_stock_from_db(country, symbol)
    if stk:
        return stk['bscs']['since']
    return None

def remove_duplicates(collection):
    print("entering remove duplicates")
    stocks = collection.find({})
    for stk in stocks:
        if stk['bscs']['symbol'] == 'DEAD':
            continue
        print(stk['bscs']['symbol'])
        entries = collection.find({"bscs.symbol" : stk['bscs']['symbol']})
        if entries.count() > 1:
            print(stk['bscs']['symbol'], entries.count())
            collection.remove({"_id" : entries[1]['_id']})

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
    update_field(col, stock['bscs']['symbol'], "num.discount_rate", 0)
    update_field(col, stock['bscs']['symbol'], "num.inflation", 0)
    update_field(col, stock['bscs']['symbol'], "num.growth_1to5", 0)
    update_field(col, stock['bscs']['symbol'], "num.growth_6to8", 0)
    update_field(col, stock['bscs']['symbol'], "num.growth_9to10", 0)
    update_field(col, stock['bscs']['symbol'], "num.growth_16to20", 0)
    update_field(col, stock['bscs']['symbol'], "num.eps", 0)
    update_field(col, stock['bscs']['symbol'], "num.eps_20yr", {})
    update_field(col, stock['bscs']['symbol'], "num.fig_yr", 0)
    update_field(col, stock['bscs']['symbol'], "num.cur_yr", 0)
    update_field(col, stock['bscs']['symbol'], "num.term_yr", 0)
    update_field(col, stock['bscs']['symbol'], "num.dcf_price", 0)
    update_field(col, stock['bscs']['symbol'], "num.dcf_years", 0)
    update_field(col, stock['bscs']['symbol'], "num.inflated_eps_price", 0)
    update_field(col, stock['bscs']['symbol'], "num.margin_of_safety", 0)
    update_field(col, stock['bscs']['symbol'], "num.dcf_return_rate", 0)
    update_field(col, stock['bscs']['symbol'], "num.cp_return_rate", 0)
    
    update_field(col, stock['bscs']['symbol'], "fig.price_growth", 0)
    update_field(col, stock['bscs']['symbol'], "fig.sales_growth", 0)
    update_field(col, stock['bscs']['symbol'], "fig.profit_growth", 0)
    update_field(col, stock['bscs']['symbol'], "fig.book_growth", 0)
    update_field(col, stock['bscs']['symbol'], "fig.cash_growth", 0)
    update_field(col, stock['bscs']['symbol'], "fig.growth", 0)
    update_field(col, stock['bscs']['symbol'], "bscs.dcf_calc", "NO")
 
def update_dcf_numbers(col, stock):
    update_field(col, stock['bscs']['symbol'], "num.discount_rate", stock['num']['discount_rate'])
    update_field(col, stock['bscs']['symbol'], "num.inflation", stock['num']['inflation'])
    update_field(col, stock['bscs']['symbol'], "num.growth_1to5", stock['num']['growth_1to5'])
    update_field(col, stock['bscs']['symbol'], "num.growth_6to8", stock['num']['growth_6to8'])
    update_field(col, stock['bscs']['symbol'], "num.growth_9to10", stock['num']['growth_9to10'])
    update_field(col, stock['bscs']['symbol'], "num.growth_16to20", stock['num']['growth_16to20'])
    update_field(col, stock['bscs']['symbol'], "num.eps", stock['fig']['ttm_eps'])
    update_field(col, stock['bscs']['symbol'], "num.eps_20yr", stock['num']['eps_20yr'])
    update_field(col, stock['bscs']['symbol'], "num.fig_yr", stock['num']['fig_yr'])
    update_field(col, stock['bscs']['symbol'], "num.cur_yr", stock['num']['cur_yr'])
    update_field(col, stock['bscs']['symbol'], "num.term_yr", stock['num']['term_yr'])
    update_field(col, stock['bscs']['symbol'], "num.dcf_price", stock['num']['dcf_price'])
    update_field(col, stock['bscs']['symbol'], "num.dcf_years", stock['num']['dcf_years'])
    update_field(col, stock['bscs']['symbol'], "num.inflated_eps_price", stock['num']['inflated_eps_price'])
    update_field(col, stock['bscs']['symbol'], "num.margin_of_safety", stock['num']['margin_of_safety'])
    update_field(col, stock['bscs']['symbol'], "num.dcf_return_rate", stock['num']['dcf_return_rate'])
    update_field(col, stock['bscs']['symbol'], "num.cp_return_rate", stock['num']['cp_return_rate'])
    
    update_field(col, stock['bscs']['symbol'], "fig.price_growth", stock['fig']['price_growth'])
    update_field(col, stock['bscs']['symbol'], "fig.sales_growth", stock['fig']['sales_growth'])
    update_field(col, stock['bscs']['symbol'], "fig.profit_growth", stock['fig']['profit_growth'])
    update_field(col, stock['bscs']['symbol'], "fig.book_growth", stock['fig']['book_growth'])
    update_field(col, stock['bscs']['symbol'], "fig.cash_growth", stock['fig']['cash_growth'])
    update_field(col, stock['bscs']['symbol'], "fig.growth", stock['fig']['growth'])
    update_field(col, stock['bscs']['symbol'], "bscs.dcf_calc", "YES")
    

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
                val = internet.get_LTP('India', stock['bscs']['symbol'])
                if val == -1:
                    PRINT_ERR("Unable to get LTP for %s"%(stock['bscs']['name']))
                else:
                    stock['bscs']['price'] = val

            print(stock['bscs'])
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
    #docs = db.US_Stocks.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    docs = db.US_Stocks.find({"bscs.dii_stake":{"$exists":False}},no_cursor_timeout=True)
    print("count: %r" %(docs.count()))
    for doc in docs:
        if i > -1:
        #if i > -1: # and not doc['bscs']['price']:
            sym = doc['bscs']['symbol']
            print("%d: %s" %(i, sym))
            url = 'https://www.barchart.com/stocks/quotes/%s/profile' %(sym)
            html_text=internet.get_webpage(url)
            update_US_stk_profile(html_text, col)
        i = i + 1

def update_US_stk_profile(html_text, collection):
    soup=parse_html.get_soup(html_text)
    s=soup.find('title').text
    symbol=re.match("(.*?) ",s).group().rstrip()
    #symbol=re.search('\(([^)]+)',s).group(1)
    #print(symbol)

    today = dt.now().date().strftime("%d-%m-%Y")
    update_field(collection, symbol, "bscs.date", today)

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
    if val and not math.isnan(val):
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
    if val and not math.isnan(val):
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
    #        cur_year = int(str(dt.now().year)[2:4])
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

# This function has been deprecated.
# It is replaced with build_US_all_stock_information()
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
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.price": to_float(stk['bscs']['price'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.volume": to_int(stk['bscs']['volume'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.mcap": to_float(stk['bscs']['mcap'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.outstanding_shares": to_int(stk['bscs']['outstanding_shares'])}})
    update_field(collection, stk['bscs']['symbol'], "bscs.price_date", dt.now())

j=0

def fork_db_process(country, sem, lock):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    num_docs = collection.find({}).count()
    if num_docs == 0:
        return

    today=str(dt.now().date())
    #Randomly get all records whose price is not updated till today
    #pipeline = [{'$sample': {'size':num_docs}},
    #            {'$match' : {"bscs.price_date": {'$ne':today}}},
    #            #{"$group": {"_id": _id, "count": {"$sum":1}}},
    #            #{"$group": {"_id": None, "total": {"$sum": 1}, "details":{"$push":{"groupby": "$_id", "count": "$count"}}}}
    #            ]
 
    #stocks = db.US_Stocks.aggregate(pipeline, allowDiskUse=True).batch_size(10)
    #stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    i=0
    for stk in stocks:
        #if ignore_stock(stk):
        #    continue
        #print("DB: %d: %s: %s"%(i,stk['bscs']['symbol'],stk['bscs']['name']))
        if 'price_failcount' in stk['bscs'].keys() and stk['bscs']['price_failcount'] > 5:
            continue
 
        sem.acquire()
        print("DB: %d: %s: %s"%(i,stk['bscs']['symbol'],stk['bscs']['name']))
        #update_stk_bscs_db(country, db, stk, sem, lock)
        threading.Thread(target=update_stk_bscs_db, args=(country, db, copy.deepcopy(stk), sem, lock,)).start()
        i = i + 1
        #break
    close_db_client(c)
    print("DB Process Stocks tried :%r"%(i))

def fork_hdf5_process(country, sem):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    sql_engine = open_sql_connection('localhost', 'root', 'petla123')

    today=str(dt.now().date())
    num_docs = collection.find({}).count()
    #num_docs = collection.find({"bscs.price_date": {'$ne':today}})
    if num_docs == 0:
        close_db_client(c)
        close_sql_connection(sql_engine)
        return

    #symbols = hdf5.get_symbols_hdf_store(country)
    #symbols = hdf5.get_symbols_from_hdf(country)
    symbols = get_symbols_from_sql(country, sql_engine)
    #symbols = get_symbols_from_mongo(collection)
    
    if country == 'India':
        indices = India_indices
    else:
        indices = US_indices 

    try:
        ##Indices
        for k in indices.keys():
            stk = {}
            stk['bscs']={}
            stk['bscs']['symbol'] = k
            stk['bscs']['name'] = indices[k]
            sem.acquire()
            #hdf5.update_dataframe_price_volume(country, db, sql_engine, stk['bscs']['symbol'], symbols, stk, sem)
            threading.Thread(target=hdf5.update_dataframe_price_volume, args=(country, db, sql_engine, stk['bscs']['symbol'], symbols, copy.deepcopy(stk), sem,)).start()

        # Randomly get all records whose price is not updated till today
        #pipeline = [{'$sample': {'size':num_docs}},
        #            {'$match' : {"bscs.price_date": {'$ne':today}}},
        #            #{"$group": {"_id": _id, "count": {"$sum":1}}},
        #            #{"$group": {"_id": None, "total": {"$sum": 1}, "details":{"$push":{"groupby": "$_id", "count": "$count"}}}}
        #            ]

        #stocks = db.US_Stocks.aggregate(pipeline, allowDiskUse=True).batch_size(10)
        #stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
 
        i=0
        t=None
        for stk in stocks:
            #if ignore_stock(stk):
            #    continue
            #if stk['bscs']['symbol'] not in symbols:
            #    print("Skipping: %r" %(stk['bscs']['symbol']))
            #    continue
            if 'price_failcount' in stk['bscs'].keys() and stk['bscs']['price_failcount'] > 5:
                print("Skipping: %r" %(stk['bscs']['symbol']))
                continue
            print("%d: Checking: %r" %(i, stk['bscs']['symbol']))
            sem.acquire()
            #hdf5.update_dataframe_price_volume(country, db, sql_engine, stk['bscs']['symbol'], symbols, stk, sem)
            t = threading.Thread(target=hdf5.update_dataframe_price_volume, args=(country, db, sql_engine, stk['bscs']['symbol'], symbols, copy.deepcopy(stk), sem,))
            t.start()
            i = i + 1

    finally:
        # Wait till all threads are completed. You can use join() instead.
        # But need to track threads and update variables.
        # Simplest way is to wait for tentative time taken for the end threads to complete
        # Randomly estimated it to be 10 sec and it perfectly works.
        time.sleep(30)
        #if t:
        #    t.join()
        close_db_client(c)
        close_sql_connection(sql_engine)
    print("HDF5 Stocks tried :%r"%(i))


# Update price, mcap, volume etc
def update_stk_bscs_db(country, db, stk, sem, lock):
    global j
    failcount=1
    try:
        today=str(dt.now().date())
        stock = internet.get_price_volume(copy.deepcopy(stk), country)
        collection = get_collection(country, db)
        if stock:
            # Update price and volume to db
            #print("%r: %r" %(stock['bscs']['symbol'], stock['bscs']['volume']))
            update_db_price_volume(collection, stock)
            j = j+1
        else:
            if 'bscs' in stk.keys() and 'price_failcount' in stk['bscs'].keys():
                failcount = failcount + stk['bscs']['price_failcount']
            # Ignore the stk for future purposes if failed to get data
            # for more than 10 times.
                if failcount > 10:
                    update_field(collection, stk['bscs']['symbol'], "bscs.trading", "NO")
                    update_field(collection, stk['bscs']['symbol'], "bscs.price_failcount", failcount)
    finally:
        sem.release()

def update_all_price_volume_db(country):
    global j
    max_threads = multiprocessing.cpu_count() * thread_factor
    hdf5_sem = threading.BoundedSemaphore(max_threads)
    db_sem = threading.BoundedSemaphore(max_threads)
    db_lock = threading.Lock()
    today=str(dt.now().date())
    count=0
    i=0

    if country != 'US' and country != 'India':
        PRINT_ERR("Unknown Country")
        return

    #fork_hdf5_process(country, hdf5_sem)
    #fork_db_process(country, db_sem, db_lock)
    hdf5_process = multiprocessing.Process(target=fork_hdf5_process, args=(country, hdf5_sem,))
    db_process = multiprocessing.Process(target=fork_db_process, args=(country, db_sem, db_lock,))
    try:
        hdf5_process.start()
        db_process.start()
    finally:
        hdf5_process.join()
        db_process.join()
    print("Exiting hdf5 and db processes")

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
                print(row[0], row[1], row[2])
                entry = []
                entry.append(sym)
                entry.append(name)
                entry.append(row[5])
                entry.append(row[6])
                entry.append(row[3])
                entry.append(row[2])
                #if "." in sym:
                #    price_change = internet.price_change('US', sym.split(".")[0], name, 365, 'HOT')
                #elif "-" in sym:
                #    price_change = internet.price_change('US', sym.split("-")[0], name, 365, 'HOT')
                #else:
                #    price_change = internet.price_change('US', sym, name, 365, 'HOT')
                #if price_change:
                #    entry.append(str(round(price_change*100, 2))+'%')
                #else:
                #    entry.append("-")
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
                    #stk = dbObject(**doc)
                    stk = doc
                    #if stk['bscs']['price'] == 0:
                    print("%d: %s: %s"%(stk['sno'],stk['bscs']['symbol'],stk['bscs']['name']))
                    write_stock_to_file(stk['bscs']['symbol'], "file2.txt", "a")
                    internet.populate_US_EPS(stk)
                    #break
    f1.close()
    f2.close()

def build_US_all_EPS():
    print("****************** Building US EPS ******************")
    db = open_db('Stocks')
    #docs = db.US_Stocks.find({"$and": [{"bscs.since":{"$exists": False}}, {"ignore":"No"}]},no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.US_Stocks.find({"bscs.since":{"$exists": False}},no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.US_Stocks.find({"bscs.symbol":"BKD"}).sort([["sno",1]])
    #docs = db.US_Stocks.find({}).sort([["sno",1]])
    #docs = db.US_Stocks.find({"fig.EPS_History":{"$exists":False}})
    #docs  = db.US_Stocks.find(get_nin("file.txt", "nins.txt"))
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"fig.DIVIDEND_History": {"$exists": False}},{"fig.Split_History": {"$exists": False}}, {"bscs.symbol":{"$ne": "ARR"}}]})
    #docs = db.US_Stocks.find({"fig.EPS_History": {"$exists": False}})
    stocks = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, ]},no_cursor_timeout=True)
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"bscs.symbol":{"$nin": ["DAIO", "IBCP", "MRTN", "SLGN"]}}]},no_cursor_timeout=True)
    count = stocks.count()
    print(count)
    if count == 0:
        print("***************** Completed fetching EPS  *************")
        return
    for stock in stocks:
        try:
            sno = stock['sno']
            if sno > 0:
                print("%d: %s: %s"%(sno,stock['bscs']['symbol'],stock['bscs']['name']))
                write_stock_to_file(stock['bscs']['symbol'], "file2.txt", "a")
                internet.populate_US_EPS(stock)
        except Exception as E:
            print(str(E))
            continue

""" Updated EPS for all existing stocks in the database"""
def update_US_all_EPS():
    db = open_db('Stocks')
    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    count = stocks.count()
    print(count)
    if count == 0:
        return
    for i, stock in enumerate(stocks):
        #if i > 50:
        #    break
        try:
            print("%d: %s: %s"%(i,stock['bscs']['symbol'],stock['bscs']['name']))
            internet.populate_US_EPS(stock)
        except Exception as E:
            print(str(E))
            continue
        
 
def build_US_all_earnings_estimates():

    db = open_db('Stocks')
    #docs = db.US_Stocks.find({"bscs.symbol":"AVGO"}).sort([["sno",1]])
    #docs = db.US_Stocks.find({}).sort([["sno",1]])
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"fig.DIVIDEND_History": {"$exists": False}},{"fig.Split_History": {"$exists": False}}, {"bscs.symbol":{"$ne": "ARR"}}]})
    #docs = db.US_Stocks.find({"quart_fig.Earning_Estimates":{"$exists":False}},no_cursor_timeout=True)
    docs = db.US_Stocks.find({},no_cursor_timeout=True)
    count = docs.count()
    print(count)
    if count == 0:
        print("***************** Completed fetching earnings estimates *************")
        return
    #try:
    today=dt.now().date()
    for doc in docs:
        sno = doc['sno']
        if sno > 0:
        #if sno > 3000:
            stk = doc
            if 'Earning_Estimates' not in stk['quart_fig'].keys() or (today - dt.strptime(stk['quart_fig']['Earning_Estimates']['date'], '%Y-%m-%d').date()) > relativedelta(months=3):
                print("%d: %s: %s"%(sno,stk['bscs']['symbol'],stk['bscs']['name']))
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
        #        #stk = dbObject(**doc)
        #        stk = doc
        #        #if stk['bscs']['price'] == 0:
        #        print("%d: %s: %s"%(sno,stk['bscs']['symbol'],stk['bscs']['name']))
        #        internet.populate_US_earnings_estimates(stk)
        #        #break
 
def build_US_quarterly_stock_information(stk):
    path = internet.get_US_quarterly_stock_page(stk['bscs']['symbol'], stk['bscs']['name'])
    for (root,dirs,files) in os.walk(path, topdown=True):
       files = [f for f in files if not f[0] == '.']
       dirs[:] = [d for d in dirs if d not in sheet.cell_value(i,0)]
       dirs[:] = [d for d in dirs if not d[0] == '.']
       #print(root)
       #print(dirs)
       #print(sorted(files))
       parse_html.populate_US_stocks_quarterly(root, sorted(files), stk)

def get_US_Stock_list():
    #nasdaq_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
    nasdaq_url="https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nasdaq&render=download"
    wb=requests.get(nasdaq_url)
    f=open(conf.nasdaq_stocks,"wb")
    f.write(wb.content)
    f.close()

    #nyse_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download"
    nyse_url="https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=nyse&render=download"
    wb=requests.get(nyse_url)
    f=open(conf.nyse_stocks,"wb")
    f.write(wb.content)
    f.close()

    #amex_url="https://www.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download"
    amex_url="https://old.nasdaq.com/screening/companies-by-name.aspx?letter=0&exchange=amex&render=download"
    wb=requests.get(amex_url)
    f=open(conf.amex_stocks,"wb")
    f.write(wb.content)
    f.close()

def build_US_All_Stocks_List():
    get_US_Stock_list()
    new_stocks = [] 
    head=["Symbol", "Name", "Sector", "Industry", "Market Cap", "$Price"]#, "Max Price Change"]
    new_stocks.append(head)
    new_stocks.extend(build_US_Stocks_List(conf.amex_stocks))
    new_stocks.extend(build_US_Stocks_List(conf.nyse_stocks))
    new_stocks.extend(build_US_Stocks_List(conf.nasdaq_stocks))
    # If atleast one new IPO
    if len(new_stocks) > 1:
        s = parse_html.html_head()
        s = parse_html.html_text(s, new_stocks)
        #s = parse_html.html_table(new_stocks)
        #print(s)
        subject = 'New Stocks :' + str(dt.now().date())
        write_to_file(s, '/tmp/new_listings.html')
        internet.send_email2('petlafin@gmail.com', 'Tasche3#Gm', 'petlafin@gmail.com', subject, s)
    return len(new_stocks)

def update_US_stock_statement(col, stk, statement_type, duration_type):
    print(statement_type,duration_type)

    #path = "/home/vpetla/work/stockanalysis/US_Stocks/html_pages/%s" %(stk['bscs']['name'])
    symbol = stk['bscs']['symbol']
    if duration_type == 'annual':
        fig = 'fig'
    else:
        fig = 'quart_fig'

    if 'financial-statements' not in stk[fig].keys():
        stk[fig]['financial-statements']={}

    if statement_type not in stk[fig]['financial-statements'].keys():
        field = fig+'.financial-statements.'+statement_type+'.'+'date'
        col.update({'bscs.symbol':stk['bscs']['symbol']},{'$set':{field:dt.now().date().strftime("%Y-%m-%d")}})
        return

    dates = list(stk[fig]['financial-statements'][statement_type].keys())
    dates.reverse()
    if 'date' in dates:
        now = dt.now().date()
        last_date = stk[fig]['financial-statements'][statement_type]['date']
        last_date = dt.strptime(last_date, "%Y-%m-%d").date()
        if (now - last_date) < relativedelta(months=1):
            print("Already updated on %r" %(str(last_date)))
            return

    # Currently page 1 is sufficient assuming the latest reports are covered in page 1.
    # If this is a new stock, it will be handled by different execution path
    i = 1
    url = "https://www.barchart.com/stocks/quotes/%s/%s/%s?reportPage=%s" %(symbol, statement_type, duration_type, i)
    #html_file = "%s/%s_%s_%s_%s.html" %(path, symbol, statement_type, duration_type, i)
    html_page = internet.get_page_with_check(url)
    if html_page is None:
        PRINT_ERR("update_US_stock_information(): Failed to get %r %r for %r" %(statement_type, duration_type, symbol))
        field = fig+'.financial-statements.'+statement_type+'.'+'date'
        col.update({'bscs.symbol':stk['bscs']['symbol']},{'$set':{field:dt.now().date().strftime("%Y-%m-%d")}})
        return
    
    if '403 ERROR' in html_page:
        PRINT_ERR("*********************** Access to Barchart blocked ******************")
        PRINT_ERR("exiting")
        sys.exit(1)

    soup = parse_html.get_soup(html_page)
    dates_before=list(stk[fig]['financial-statements'][statement_type].keys())
    if 'date' in dates_before:
        dates_before.remove('date')
    stk = parse_html.populate_statement(soup, stk, statement_type, duration_type)
    dates_after=list(stk[fig]['financial-statements'][statement_type].keys())
    if 'date' in dates_after:
        dates_after.remove('date')

    #dates = list(statements.keys())
    #dates.reverse()
    #for i, d in enumerate(dates):
    #    #if type(d) is datetime.date:
    #    if True:
    #        if statement_type == 'balance-sheet':
    #            if 'Current Assets' in statements[d]['Assets'].keys():
    #                del statements[d]['Assets']['Current Assets']
    #            if 'Non-Current Assets' in statements[d]['Assets'].keys():
    #                del statements[d]['Assets']['Non-Current Assets']
    #            if 'Current Liabilities' in statements[d]['Assets'].keys():
    #                del statements[d]['Liabilities']['Current Liabilities']
    #            if 'Non-Current Liabilities' in statements[d]['Assets'].keys():
    #                del statements[d]['Liabilities']['Non-Current Liabilities']

    if len(dates_after) > len(dates_before):
        statements = stk[fig]['financial-statements'][statement_type]
        field = fig+'.financial-statements.'+statement_type#+'.'+d.strftime('%m-%Y')
        col.update({'bscs.symbol':stk['bscs']['symbol']},{'$set':{field:statements}})
        print("%s %s updated"%(fig, statement_type))
        print("New entries: %r" %(list(set(dates_after)-set(dates_before))))

    field = fig+'.financial-statements.'+statement_type+'.'+'date'
    col.update({'bscs.symbol':stk['bscs']['symbol']},{'$set':{field:dt.now().date().strftime("%Y-%m-%d")}})

def update_US_stock_information(col, stk):
    #db = open_db('test')
    #col = db.col
    #income statements
    update_US_stock_statement(col, stk, "income-statement", "annual")
    update_US_stock_statement(col, stk, "income-statement", "quarterly")
    #cash flow statements
    update_US_stock_statement(col, stk, "cash-flow", "annual")
    update_US_stock_statement(col, stk, "cash-flow", "quarterly")
    #balance sheet statements
    update_US_stock_statement(col, stk, "balance-sheet", "annual")
    update_US_stock_statement(col, stk, "balance-sheet", "quarterly")

def update_US_all_stock_information():
    db = open_db('Stocks')

    #s=[]
    #f = open("stocks.txt","r")
    #for line in f:
    #    line = line.replace("\n","")
    #    s.append(line)
    #if len(s) > 0:
    #    del s[-1]
    #syms = {"$nin" : s}
    #stocks_list = db.US_Stocks_List.find({"symbol":syms}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r: %r" %(i, stk['bscs']['symbol'], stk['bscs']['name']))
        update_US_stock_information(db.US_Stocks, stk)
        #if i > 10:
        #    break

def build_US_stock_information(doc):
    db   = open_db('Stocks')
    sym  = doc['symbol']
    name = doc['Name']

    name = name.replace(",","").lstrip().rstrip()
    name = name.replace("&#39;", "\'")
    name = name.replace("/", "")
    name = name.replace("?", "")
    name = name.replace("*", "")
    sym = sym.replace("^", "-").lstrip().rstrip()
    sym = sym.replace("~", "").lstrip().rstrip()
    sym = sym.replace("?", "").lstrip().rstrip()
    db.US_Stocks_List.update({'Name': doc['Name']}, {'$set': {"Name": name}})
    db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"symbol": sym}})

    stocks = db.US_Stocks.find({"bscs.symbol":sym})
    if stocks.count() == 0:
        print("%d: %s: %s "%(doc['sno'],doc['symbol'], doc['Name']))
        # Get financial data from the internet
        path = internet.get_US_stock_page(sym, name)
        
        path = "/home/vpetla/work/stockanalysis/US_Stocks/html_pages/%s" %(name)
        path = path.lstrip().rstrip().replace(",","")
        
        ret=True
        for (root,dirs,files) in os.walk(path, topdown=True):
            files = [f for f in files if not f[0] == '.']
            dirs[:] = [d for d in dirs if d not in sheet.cell_value(i,0)]
            dirs[:] = [d for d in dirs if not d[0] == '.']
            #print("Root: %r" %(root))
            #print(dirs)

            #Sort strings with numbers
            # natural_keys() is a function defined in common.py
            files.sort(key=natural_keys)
            #print(files)

            stock = {}
            ret = parse_html.populate_US_stocks(db, root, files, stock, sym, name, doc['Sector'], doc['Industry']) 
        if ret is True:
            db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"data": "YES"}})
            #write_stock_to_file(doc['symbol'], "stocks.txt", "a")
            remove_dir(path)
    db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})
 
def build_US_all_stock_information():
    j=0
    db = open_db('Stocks')

    #s=[]
    #f = open("stocks.txt","r")
    #for line in f:
    #    line = line.replace("\n","")
    #    s.append(line)
    #if len(s) > 0:
    #    del s[-1]
    #syms = {"$nin" : s}
    #stocks_list = db.US_Stocks_List.find({"symbol":syms}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    stocks_list = db.US_Stocks_List.find({'parsed':'NO'},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print("Number of stocks not yet parsed: %r" %(stocks_list.count()))

    remove_dir('/home/vpetla/work/stockanalysis/US_Stocks/html_pages')
    create_dir('/home/vpetla/work/stockanalysis/US_Stocks/html_pages')

    for doc in stocks_list:
        sno = doc['sno']
        if sno > 0:
            #name = doc['Name']
            #if name.find("Fund") != -1 or name.find("Trust") != -1:
            #    print("Skipping: %r" %(name))
            #    db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})
            #    continue

            build_US_stock_information(doc)

    #set_sno('US')
    # Create index based on sno
    #db.US_Stocks.createIndex({sno: -1})
    #db.US_Stocks.createIndex({ "$**": "text" },{ name: "TextIndex" })

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
    close_db()

def get_beta(country, sym, sdate, edate, df=None):
    betas = {}
    if df is None:
        try:
            #from pandas_datareader.quandl import QuandlReader
            #df = pdr.get_data_stooq(sym, sdate, edate, retry_count=3)
            #print(df)
            #df = hdf5.get_dataframe(country, sym, sdate, edate)
            df = hdf5.read_from_hdf(country, sym, sdate, edate)
        except Exception as e:
            print("Could not get data. Failed to calculate beta")
            return None
    if df.empty:
        return None

    if pd.to_datetime(edate) < df.index[0]:
        return None

    if country == 'US':
        bindex = "SP500"
    elif country == 'India':
        bindex = "BSE" 
    else:
        PRINT_ERROR("Unknown country. Unable to calculate beta for %s" %(sym))
        return betas

    #dfb = hdf5.get_dataframe(country, bindex, df.index[0], df.index[-1])
    dfb = hdf5.read_from_hdf(country, bindex, pd.Timestamp(df.index[0]).date(), pd.Timestamp(df.index[-1]).date())
    #dfb = hdf5.get_dataframe(country, bindex, sdate, edate)
   
    # Calculate CAGR
    s_first = df['Adj Close'][0]
    if isinstance(s_first, complex):
        print("first is complex number")
    s_last = df['Adj Close'][-1]
    if isinstance(s_last, complex):
        print("last is complex number")
    #print(df['Adj Close'].head(5))
    #print(df['Adj Close'].tail(5))
    try:
        years = (edate-sdate).days/365.25
    except Exception:
        print("edate: %s, sdate: %s"%(edate,sdate))
        sys.exit(1)

    #print("sdate: %r, edate: %r, last: %r, first: %r"%(sdate, edate, last, first))
    growth_percent = s_last/s_first - 1
    if years == 0:
        cagr = None
    else:
        try:
            cagr = round((((s_last/s_first)**(1/years))-1), 4)
        except Exception as e:
            print(str(e))
            print("Failed to calculate CAGR for : %r" %(sym))
            print("First: %r, last: %r, years: %r" %(s_first, s_last, years))
            cagr = None
            #sys.exit()

    ## Take symbol's indexes as inputs
    ## For example, the recession happened in 2008.
    ## If the symbol started trading in 2011, the symbol's dataframe will not have
    ## info in 2008 but the S&P 500 does. The S&P 500 then takes the entries of 2008
    ## and uses it as the start where as the symbol started in 2011.
    ## To avoid this ambiquity, take symbol's timestamps as the indices for the S&P500
    ## (Pdb) df.index[0]
    ## Timestamp('2011-01-26 00:00:00')
    ## (Pdb) df.index[-1]
    ## Timestamp('2019-11-15 00:00:00')
    ## (Pdb)
    # Taken care above. Not required here
    #dfb = dfb[df.index[0]:df.index[-1]]

    first = dfb['Adj Close'][0]
    last  = dfb['Adj Close'][-1]

    bgrowth_percent = last/first - 1
    if years == 0:
        b_cagr = None
    else:
        b_cagr = round((((last/first)**(1/years))-1), 4)
    #print("Years: %r, first: %r, last: %r, cagr: %r, cagr_b: %r" %(round(years,2), first, last, round(cagr,4), round(b_cagr,4)))

    # from daily data points, create a time-series of monthly data points
    if edate-sdate < timedelta(days=31):
        duration='d'
        time_period = 31/(edate-sdate).days * 12
    else:
        duration = 'M'
        time_period=12. #months

    rts = df.resample(duration).last()
    rbts = dfb.resample(duration).last()
    dfsm = pd.DataFrame({'s_adjclose' : rts['Adj Close'],
                            'b_adjclose' : rbts['Adj Close']},
                            index=rts.index)
    
    # compute returns
    dfsm[['s_returns','b_returns']] = dfsm[['s_adjclose','b_adjclose']]/\
        dfsm[['s_adjclose','b_adjclose']].shift(1) -1
    dfsm = dfsm.dropna()
    try:
        covmat = np.cov(dfsm["s_returns"],dfsm["b_returns"])
    except Exception as E:
        print("sym: %r covmat: %r, %r" %(sym, covmat, str(E)))
    
    index_change = dfb['Adj Close'].pct_change()
    beta = df['Adj Close'].pct_change().cov(index_change) / index_change.var()
    
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
    if cagr:
        alpha_pure = round(cagr - b_cagr, 4)
    else:
        alpha_pure = 0
    #print("alpha/year: %r" %(alpha))
    #print("alpha_pure/year: %r" %(alpha_pure))
    volatility = volatility*np.sqrt(time_period)
 
    betas.update({"Start_Price":float(s_first)})
    betas.update({"End_Price":float(s_last)})
    betas.update({"Start_Date":str(df.index[0].date())})
    betas.update({"End_Date":str(df.index[-1].date())})
    betas.update({"Index_CAGR":b_cagr})
    betas.update({"Index_Percent_Change":bgrowth_percent})
    betas.update({"CAGR":cagr})
    betas.update({"Percent_Change":growth_percent})
    betas.update({"beta":beta})
    betas.update({"alpha":alpha})
    betas.update({"alpha_pure":alpha_pure})
    betas.update({"r_squared":r_squared})
    betas.update({"volatility":volatility})
    betas.update({"avg_price":df['Adj Close'].mean()})
    #print(betas)

    # Only for recession betas
    if edate != dt.now().date():
        try:
            #from pandas_datareader.quandl import QuandlReader
            #df = pdr.get_data_stooq(sym, sdate, edate, retry_count=3)
            #print(df)
            df = hdf5.read_from_hdf(country, sym, edate)
            # Calculate CAGR
            s_first = df['Adj Close'][0]
            if isinstance(s_first, complex):
                print("first is complex number")
            s_last = df['Adj Close'][-1]
            if isinstance(s_last, complex):
                print("last is complex number")
            growth_percent = s_last/s_first - 1
            betas.update({"since_then":growth_percent})
        except Exception as e:
            betas.update({"since_then":nan})
        try:
            sdate = edate
            edate = dt.strptime(recessions[list(recessions.keys())[-1]]['start'], "%d %B %Y").date()
            df = hdf5.read_from_hdf(country, sym, sdate, edate)
            # Calculate CAGR
            s_first = df['Adj Close'][0]
            if isinstance(s_first, complex):
                print("first is complex number")
            s_last = df['Adj Close'][-1]
            if isinstance(s_last, complex):
                print("last is complex number")
            growth_percent = s_last/s_first - 1
            betas.update({"since_then_till_last_recession":growth_percent})
        except Exception as e:
            betas.update({"since_then_till_last_recession":nan})
 
    return betas
    #print (stock, beta, alpha, r_squared, volatility, momentum)
    
def update_stock_recession_betas(country, collection, doc, sym, df=None):
    years = recessions.keys()

    for year in years:
        try:
            #if not 'recession' in doc['fig']['betas'].keys() or not year in doc['fig']['betas']['recession'].keys():
            if True:
                #print("Recession Betas")
                st_date = dt.strptime(recessions[year]['start'], "%d %B %Y").date()
                if 'end' in recessions[year].keys():
                    en_date = dt.strptime(recessions[year]['end'], "%d %B %Y").date()
                else:
                    en_date = dt.now().date()
                #print(st_date)
                #print(en_date)
                betas = get_beta(country, sym, st_date, en_date, df=None)
                #print("Beta: %r" %(betas))
                field="fig.betas.recession.%s" %(year)
                collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        except KeyError:
                #print("Recession Betas")
                st_date = dt.strptime(recessions[year]['start'], "%d %B %Y").date()
                en_date = dt.strptime(recessions[year]['end'], "%d %B %Y").date()
                #print(st_date)
                #print(en_date)
                betas = get_beta(country, sym, st_date, en_date, df=None)
                #print("Beta: %r" %(betas))
                field="fig.betas.recession.%s" %(year)
                collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
    return

def update_stock_betas2(country, stk, df=None):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    try:
        update_stock_betas(country, collection, stk, sem=None, df=df)
    finally:
        close_db_client(c)

def update_stock_betas(country, collection, stk, sem=None, df=None):
    try:
        sym = stk['bscs']['symbol']
        print("beta: %r: %r" %(stk['sno'], sym))
        if 'since' not in stk['bscs'].keys():
            stk  = update_since_dataframe(country, collection, stk)

        since = stk['bscs']['since']
        #print("since: %r" %(since))
        #sno = int(read_from_file("beta.txt"))
        #if sno > stk['sno']:
        #    continue
        since_start = dt.strptime(since, "%Y-%m-%d").date()
        
        update_stock_recession_betas(country, collection, stk, sym, df=df)
        
        #print(stk['fig']['betas'].keys())
        #Since last recession
        betas = None
        year = sorted(recessions.keys())[-1]
        st_date = dt.strptime(recessions['2007']['end'], "%d %B %Y").date()
        en_date = dt.now().date()
        #print("Since last recession")
        #print(st_date)
        #print(en_date)
        betas = get_beta(country, sym, st_date, en_date, df=df)
        #print("Betas: %r" %(betas))
        field="fig.betas.since_last_recession"
        collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        
        #whole beta
        #print("whole beta")
        st_date = since_start
        en_date = dt.now().date()
        #print(st_date)
        #print(en_date)
        betas = get_beta(country, sym, st_date, en_date, df=df)
        #print("Betas: %r" %(betas))
        field="fig.betas.whole"
        collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        
        #10 year beta
        #print("10 year beta")
        en_date = dt.now().date()
        betas = None
        st_date = en_date - relativedelta(years=10)
        #print(st_date)
        #print(en_date)
        betas = get_beta(country, sym, st_date, en_date, df=df)
        #print("Betas: %r" %(betas))
        field="fig.betas.ten_year"
        collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        
        #5 year beta
        #print("5 year beta")
        en_date = dt.now().date()
        betas = None
        st_date = en_date - relativedelta(years=5)
        #print(st_date)
        #print(en_date)
        betas = get_beta(country, sym, st_date, en_date, df=df)
        #print("Betas: %r" %(betas))
        field="fig.betas.five_year"
        collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        
        #1 year beta
        #print("1 year beta")
        en_date = dt.now().date()
        betas = None
        st_date = en_date - relativedelta(years=1)
        #print(st_date)
        #print(en_date)
        betas = get_beta(country, sym, st_date, en_date, df=df)
        field="fig.betas.one_year"
        #print("Betas: %r" %(betas))
        collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        
        #6 months beta
        #print("6 months beta")
        en_date = dt.now().date()
        betas = None
        st_date = en_date - relativedelta(months=6)
        #print(st_date)
        #print(en_date)
        betas = get_beta(country, sym, st_date, en_date, df=df)
        field="fig.betas.six_months"
        #print("Betas: %r" %(betas))
        collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
    
    finally:
        if sem:
            sem.release()

def update_all_stock_betas(country):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)

    #docs = db.find({"$or": [{"fig.betas.recession": {"$exists": False}},{"fig.betas.since_last_recession": {"$exists": False}}, {"fig.betas.whole": {"$exists": False}}, {"fig.betas.five_year": {"$exists": False}}, {"fig.betas.one_year": {"$exists": False}}, {"fig.betas.six_months": {"$exists": False}}]}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({ "$and": [{"$or": [{"fig.betas.recession": {"$exists": False}},{"fig.betas.since_last_recession": {"$exists": False}}, {"fig.betas.whole": {"$exists": False}}, {"fig.betas.five_year": {"$exists": False}}, {"fig.betas.one_year": {"$exists": False}}, {"fig.betas.six_months": {"$exists": False}}]}, {"bscs.symbol":{"$nin" : ["AAN", "GOLF", "SFS"]}}]}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = collection.find({"fig.betas": {"$exists": False}},no_cursor_timeout=True).sort([["sno",1]])
    docs = collection.find({}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({"bscs.symbol":{"$in" : ["MKTX"]}}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({"bscs.symbol":{"$nin" : ["LABL", "LEXEB", "HF", "AMBR", "AAN", "SFS", "HRS", "LLL", "CZFC", "LION", "JSYN", "LGCY", "PYDS"]}}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print("Total Stocks: %r" %(docs.count()))

    max_threads = multiprocessing.cpu_count() * thread_factor
    sem = threading.BoundedSemaphore(max_threads)

    for doc in docs:
        #if ignore_stock(doc):
        #    continue
        sem.acquire()
        update_stock_betas(country, collection, copy.deepcopy(doc), sem)
        #threading.Thread(target=update_stock_betas, args=(country, collection, copy.deepcopy(doc), sem,)).start()

    time.sleep(10)
    close_db_client(c)
 
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

    close_db()

def remove_nested(stmt):
    dates=list(stmt.keys())
    
    entry={}
    for d in dates:
        stmt_d = stmt[d]
        fields = list(stmt_d.keys())
        for f in fields:
            entry.update(stmt_d.pop(f,{}))
        stmt[d] = entry
        entry = {}
    return stmt

def form_df(stmt, stmt_type):
    try:
        del stmt['date']
    except:
        pass
    if stmt_type != 'income-statement':
        stmt = remove_nested(copy.deepcopy(stmt))
    df=pd.DataFrame.from_dict(stmt)
    df=pd.DataFrame.transpose(df)
    df.index=pd.to_datetime(df.index)
    #df=df.sort_index()
    df.sort_index(ascending=True, inplace=True)
    return df

def build_df_from_stmt(stk, stmt, df, fields):
    df_cols=list(df.columns)
    
    # It is not necessary that all columns should be present.
    # Take whatever are available
    available_cols=[]        
    for f in fields:
        if f in df_cols:
            available_cols.append(f)
    df = df[available_cols]
    renamed_cols = {}
    for c in available_cols:
        renamed_cols[c] = c.replace(' ','_') # Replace spaces with '_' for storing convinience in mysql
    df.rename(columns=renamed_cols, inplace=True)
    
    # Add new columns to the dataframe
    for i, c in enumerate(df.columns):
        s = c + percents[i]
        df[s]=None
    
    df, status = update_percent_change(df, fields=fin_fields, duration=fin_durations)
    return df, status

def fin_percent_change_row(key, index, c, d, df, duration=None):
    nan_flag = False
    cur_val = d[c]
    cur_date = pd.to_datetime(index).date()
    #cur_loc = hdf5.get_nearest_index(df, cur_date)
    cur_loc = df.index.get_loc(index)
   
    if duration is None: # Whole percentage case
        start_loc = 0
        start_date = pd.to_datetime(df.index[0]).date()
    else:
        start_date = cur_date - duration
        start_loc = hdf5.get_nearest_index(df, start_date)

    if start_loc == cur_loc:
        change = 0
    else:
        # Get the first non nan value and non-zero from the set of records
        start_val = df.iloc[start_loc][c]
        if isnan(start_val):
            nan_flag = True
            start_index = df.iloc[start_loc:cur_loc+1][c].first_valid_index()
            if start_index:
                start_loc = df.index.get_loc(start_index)
                #start_date = pd.to_datetime(start_index).date()
                if start_loc is not None:
                    start_val = df.iloc[start_loc][c]
                else:
                    start_val = nan
            else:
                start_val = nan
        # Assuming a value of zero or nan means wrong value.
        # Skip and ignore such values and take the most latest value
        if start_val == 0:
            #start_loc = df.iloc[start_loc:cur_loc+1][c].ne(0).idxmax()
            nonzerodf = df.iloc[start_loc:cur_loc+1][c].ne(0)
            start_loc = None
            for i in nonzerodf.index:
                if nonzerodf[i] == True: # dont use 'is True'
                    start_loc = df.index.get_loc(i)
                    break
            #start_loc = df.index.get_loc(start_loc)
            if start_loc is not None:
                start_val = df[c].iloc[start_loc]
            else:
                # It means all column values are zero from start_loc to cur_loc
                start_val = 0
                start_loc = cur_loc
        if not isnan(start_val) and not isnan(cur_val):
            # If both are same her instead of in line 1946. It 
            # means that there are zero and nan elements in the 
            # actual start location which has caused the code to pick
            # the first nonzero and non-nan elements.
            # It couldn't find such element till the current location.
            # In that case, the change will be same as cur_val.
            if start_loc == cur_loc:
                change = 0
                ## If there are no start values and the column starts
                ## with cur_val then the percentage change is zero.
                #if nan_flag:
                #    change = 0
                #else:
                #    change = cur_val
            # Sometimes, the first non-zero value loc is greater than cur_loc.
            # In that case, the percent change should be nan.
            elif start_loc < cur_loc:
                change = percent_change(start_val, cur_val)
            else:
                change = nan
        else:
            change = nan
    df[key][index] = change
    return df

def fin_change(df, fig):
    #st_price = read.iat[0, read.columns.get_loc('close')]
    #en_price = read.iat[-1, read.columns.get_loc('close')]

    #df.index= pd.to_datetime(df.index)
    if fig == 'fig':
        fields    = fin_year_fields
        datatypes = fin_year_fields_datatypes
        durations = fin_year_price_durations
        ret_index = pd.DatetimeIndex.strftime(df.index, "%Y-%m")
    else:
        fields    = fin_quarter_fields
        datatypes = fin_quarter_fields_datatypes
        durations = fin_quarter_price_durations
        ret_index = pd.DatetimeIndex.strftime(df.index, "%Y-%m-%d")

    # Create new fields
    cols = list(df.columns)
    for c in cols:
        for i in range(len(durations)):
            key = '{}_{}'.format(c,fields[i])
            key = key.replace('- ','').replace(' ', '_')
            print(key)
            if key not in list(df.keys()):
                df[key]=nan
            duration = durations[i]
            for index, d in df.iloc[1:].iterrows():
                df = fin_percent_change_row(key, index, c, d, df, duration)
                #cur_val = d[c]
                #cur_date = pd.to_datetime(index).date()
                ##cur_loc = hdf5.get_nearest_index(df, cur_date)
                #cur_loc = df.index.get_loc(index)

                #start_date = cur_date - duration
                #start_loc = hdf5.get_nearest_index(df, start_date)
                #if start_loc == cur_loc:
                #    change = 0
                #else:
                #    # Get the first non nan value and non-zero from the set of records
                #    start_val = df.iloc[start_loc][c]
                #    if isnan(start_val):
                #        start_index = df.iloc[start_loc:cur_loc+1][c].first_valid_index()
                #        if start_index:
                #            start_loc = df.index.get_loc(start_index)
                #            #start_date = pd.to_datetime(start_index).date()
                #            if start_loc is not None:
                #                start_val = df.iloc[start_loc][c]
                #            else:
                #                start_val = nan
                #        else:
                #            start_val = nan
                #    # Assuming a value of zero or nan means wrong value.
                #    # Skip and ignore such values and take the most latest value
                #    if start_val == 0:
                #        #start_loc = df.iloc[start_loc:cur_loc+1][c].ne(0).idxmax()
                #        nonzerodf = df.iloc[start_loc:cur_loc+1][c].ne(0)
                #        start_loc = None
                #        for i in nonzerodf.index:
                #            if nonzerodf[i] == True: # dont use 'is True'
                #                start_loc = df.index.get_loc(i)
                #                break
                #        #start_loc = df.index.get_loc(start_loc)
                #        if start_loc is not None:
                #            start_val = df[c].iloc[start_loc]
                #        else:
                #            # It means all column values are zero from start_loc to cur_loc
                #            start_val = 0
                #            start_loc = cur_loc
                #    if not isnan(start_val) and not isnan(cur_val):
                #        # If both are same her instead of in line 1946. It 
                #        # means that there are zero and nan elements in the 
                #        # actual start location which has caused the code to pick
                #        # the first nonzero and non-nan elements.
                #        # It couldn't find such element till the current location.
                #        # In that case, the change will be same as cur_val.
                #        if start_loc == cur_loc:
                #            change = cur_val
                #        # Sometimes, the first non-zero value loc is greater than cur_loc.
                #        # In that case, the percent change should be nan.
                #        elif start_loc < cur_loc:
                #            change = percent_change(start_val, cur_val)
                #        else:
                #            change = nan
                #    else:
                #        change = nan
                #df[key][index] = change

        # Whole Change Case
        key = '{}_{}'.format(c,fields[-1])
        key = key.replace(' ', '_')
        if key not in list(df.keys()):
            df[key]=nan
        print(key)
        for index, d in df.iloc[1:].iterrows():
            df = fin_percent_change_row(key, index, c, d, df)

        ## Get the first non nan value and non-zero from the set of records
        ##start_val = df.loc[df[c].first_valid_index()][c]
        #start_loc = df[c].ne(0).idxmax()
        #start_loc = df.index.get_loc(start_loc)
        #start_val = df[c].iloc[start_loc]
        #for index, d in df.iloc[1:].iterrows():
        #    # whole change
        #    cur_loc = df.index.get_loc(index)
        #    # Sometimes, the first non-zero value loc is greater than cur_loc.
        #    # In that case, the percent change should be nan.
        #    if start_loc < cur_loc:
        #        change = percent_change(start_val, d[c])
        #    else:
        #        change = nan
        #    df[key][index] = change

    df.index = ret_index
    return df
#                wdf.loc[cur_date_str]=nan
#                wdf.loc[cur_date_str]['date'] = cur_date_str
#                #percent changes for day, week, month etc
#                for i in range(len(price_change_durations)):
#                    start_price = db.mysql_get_price(sql_engine, table_name, str(cur_date - price_change_durations[i]), str(cur_date))
#                    change = percent_change(start_price, cur_price)
#                    wdf.loc[cur_date_str][price_change_fields[i]] = change
#
#
# 
#
#    miss = mysql_add_columns(mysql_engine, table_name, missing_cols)
#    table_name = db.get_symbol_table_name(sym)
#
#    wdf = pd.dataframe(columns=['date']+price_change_fields) 
#
#    try:
#        if db.mysql_exists_table(sql_engine, table_name):
#            #query = 'select `date`, `adj close` from %s order by date' %(table_name)
#            query = 'select `date`, `adj close` from %s where `day change` is null order by date' %(table_name)
#            #query = 'select `date`, `adj close`, {} from {}'.format(', '.join(['`{}`'.format(c) for c in price_change_fields]), table_name)
#            df = db.read_from_sql(query, sql_engine)
#            if df.empty:
#                return
#
#            ipo_price = df['adj close'][0]
#
#            for index, d in df.iloc[1:].iterrows():
#                cur_price = d['adj close']
#                cur_date = pd.to_datetime(index).date()
#                cur_date_str = str(cur_date)
#                wdf.loc[cur_date_str]=nan
#                wdf.loc[cur_date_str]['date'] = cur_date_str
#                #percent changes for day, week, month etc
#                for i in range(len(price_change_durations)):
#                    start_price = db.mysql_get_price(sql_engine, table_name, str(cur_date - price_change_durations[i]), str(cur_date))
#                    change = percent_change(start_price, cur_price)
#                    wdf.loc[cur_date_str][price_change_fields[i]] = change
#
#                # whole change
#                change = percent_change(ipo_price, cur_price)
#                wdf.loc[cur_date_str][price_change_fields[-1]] = change
#                #wdf.drop(wdf.index, inplace=true)
#
#            print("mysql: percent_change: %s"%(sym))
#            db.mysql_update_table(sql_engine, table_name, wdf)
#
#            query = 'select `date`, {} from {} order by date desc limit 2'.format(', '.join(['`{}`'.format(c) for c in price_change_fields]), table_name)
#            df = db.read_from_sql(query, sql_engine)
#
#            change = get_change(df, 'day change')
#            db.update_field(collection, sym, "price_change.day", change)
#
#            change = get_change(df, 'week change')
#            db.update_field(collection, sym, "price_change.week", change)
#
#            change = get_change(df, 'month change')
#            db.update_field(collection, sym, "price_change.month", change)
#
#            change = get_change(df, 'quarter change')
#            db.update_field(collection, sym, "price_change.quarter", change)
#
#            change = get_change(df, 'half year change')
#            db.update_field(collection, sym, "price_change.half_year", change)
#
#            change = get_change(df, 'year change')
#            db.update_field(collection, sym, "price_change.year", change)
#
#            change = get_change(df, 'five year change')
#            db.update_field(collection, sym, "price_change.five_year", change)
#
#            change = get_change(df, 'ten year change')
#            db.update_field(collection, sym, "price_change.ten_year", change)
#
#            change = get_change(df, 'whole change')
#            db.update_field(collection, sym, "price_change.whole", change)
#
#            end_date = str(dt.now().date())
#            #get 52 week high
#            #select max(`adj close`) from stksp500 where date between date_sub('2020-03-20', interval 1 year) and '2020-03-20';
#            query ='select max(`adj close`) from {} where date between date_sub(\'{}\', interval 1 year) and \'{}\''.format(table_name, end_date, end_date)
#            result=sql_engine.execute(query)
#            high_price = result.first()[0]
#            #high_price = hdf5.hdf_get_high_n_days(df, 365)
#            db.update_field(collection, sym, "bscs.fiftytwoweek_high", high_price)
#            #get 52 week low
#            query ='select min(`adj close`) from {} where date between date_sub(\'{}\', interval 1 year) and \'{}\''.format(table_name, end_date, end_date)
#            #query ='select min(`adj close`) from ' + table_name + ' where date between date between date_sub(%s, interval 1 year);'%(end_date, end_date)
#            result=sql_engine.execute(query)
#            low_price = result.first()[0]
#            #low_price = hdf5.hdf_get_low_n_days(df, 365)
#            db.update_field(collection, sym, "bscs.fiftytwoweek_low", low_price)
#
#            # get today's price
#            query = 'select `adj close` from {} order by date desc limit 1'.format(table_name)
#            result=sql_engine.execute(query)
#            price = result.first()[0]
#            #price = hdf5.hdf_get_price(sym, df, dt.now().date())
#            
#            if high_price == 0:
#                change = 0
#            else:
#                change = (price/high_price) - 1
#
#            db.update_field(collection, sym, "price_change.with_52week_high", change)
#            
#            if low_price == 0:
#                change = 0
#            else:
#                change = (price/low_price) - 1
#
#            db.update_field(collection, sym, "price_change.with_52week_low", change)
#        else:
#            change=none
#            db.update_field(collection, sym, "price_change.day", change)
#            db.update_field(collection, sym, "price_change.week", change)
#            db.update_field(collection, sym, "price_change.month", change)
#            db.update_field(collection, sym, "price_change.quarter", change)
#            db.update_field(collection, sym, "price_change.half_year", change)
#            db.update_field(collection, sym, "price_change.year", change)
#            db.update_field(collection, sym, "price_change.whole", change)
#            db.update_field(collection, sym, "bscs.fiftytwoweek_high", change)
#            db.update_field(collection, sym, "bscs.fiftytwoweek_low", change)
#            db.update_field(collection, sym, "price_change.with_52week_high", change)
#            db.update_field(collection, sym, "price_change.with_52week_low", change)
# 
#    finally:
#        db.update_field(collection, sym, "price_change.date", dt.now())
#        if sem:
#            sem.release()
#

def update_US_fin_percent_change(db, mysql_engine, stk, fig):
    if fig == 'fig':
        fin_fields = fin_year_fields
        fin_durations = fin_year_price_durations
    else:
        fin_fields = fin_quarter_fields
        fin_durations = fin_quarter_price_durations

    if fig not in stk.keys():
        print("No financial figures available. Exiting percent calculation")
        return
    if 'financial-statements' not in stk[fig].keys():
        print("No financial figures available. Exiting percent calculation")
        return

    if 'income-statement' in stk[fig]['financial-statements'].keys():
        #fields=['Sales', 'Operating Expenses', 'Gross Profit', 'Net Income $M']
        df = form_df(stk[fig]['financial-statements']['income-statement'], 'income-statement')
        #df_cols=list(df.columns)
        # Get available columns in the mongodb. Not all fields might be available
        #available_cols=[]
        #for f in fields:
        #    if f in df_cols:
        #        available_cols.append(f)
        df = fin_change(df, fig)
    
       #check_n_write_to_sql(mysql_engine, stk['bscs']['symbol'], df, list(df.columns))

    if 'balance-sheet' in stk[fig]['financial-statements'].keys():
        df = form_df(stk[fig]['financial-statements']['balance-sheet'], 'balance-sheet')
        df = fin_change(df, fig)
        #fields=['Total Current Assets', 'Total Non-Current Assets', 'Total Assets $M', 'Intangibles', 'Total Current Liabilities', 'Total Non-Current Liabilities', 'Total liabilities', 'Long Term Debt $M', 'Common Shares']
        #df_cols=list(df.columns)

        ## Get available columns in the mongodb. Not all fields might be available
        #available_cols=[]
        #for f in fields:
        #    if f in df_cols:
        #        available_cols.append(f)
        #bdf = copy.deepcopy(df[available_cols])
        #del df

        #renamed_cols = {}
        #for c in available_cols:
        #    renamed_cols[c] = c.replace(' ','_') # Replace spaces with '_' for storing convinience in mysql
        #bdf.rename(columns=renamed_cols, inplace=True)

    if 'cash-flow' in stk[fig]['financial-statements'].keys():
        df = form_df(stk[fig]['financial-statements']['cash-flow'], 'cash-flow')
        df = fin_change(df, fig)
        #fields=['Operating Cash Flow', 'PPE Investments', 'Free Cash Flow', 'Capital Expenditure']
        #df_cols=list(df.columns)
        #available_cols=[]
        #for f in fields:
        #    if f in df_cols:
        #        available_cols.append(f)
        #cdf = df[available_cols]
        #del df
        #renamed_cols = {}
        #for c in available_cols:
        #    renamed_cols[c] = c.replace(' ','_') # Replace spaces with '_' for storing convinience in mysql
        #bdf.rename(columns=renamed_cols, inplace=True)

# Calculate percentage change of the annual/quarter fundamental params
# like sales, profits, cash flows, tangible/total book value etc
def update_all_US_fin_percent_change():
    db = open_db('Stocks')
    mysql_engine = sqlalchemy.create_engine("mysql+pymysql://root:petla123@10.0.0.12:3306/US_Stocks_Fin", pool_size=1)

    stocks = db.US_Stocks.find({'bscs.symbol':'AAPL'}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r: %r" %(i, stk['bscs']['symbol'], stk['bscs']['name']))
        update_US_fin_percent_change(db, mysql_engine, stk, 'fig')
        update_US_fin_percent_change(db, mysql_engine, stk, 'quart_fig')

    close_db()
    mysql_engine.dispose()

def correct_error(stmt, stmt_type):
    miss_count = 0
    dates=list(stmt.keys())
    
    for d in dates:
        if d == 'date':
            continue
        try:
            if stmt_type == 'balance-sheet':
                if 'TOTAL' in stmt[d]['Assets'].keys():
                    stmt[d]['Assets']['Total Current Assets'] = \
                                                            safe_substract( \
                                                                stmt[d]['Assets']['Total Assets $M'], \
                                                                stmt[d]['Assets']['TOTAL'])

                    stmt[d]['Assets']['Total Non-Current Assets'] = stmt[d]['Assets']['TOTAL']
                    del stmt[d]['Assets']['TOTAL']
                else:
                    print("%s: %s Assets[TOTAL] is missing" %(stmt_type,d))
                    miss_count=1
                if 'TOTAL' in stmt[d]['Liabilities'].keys():
                    stmt[d]['Liabilities']['Total Current Liabilities'] = \
                                                            safe_substract( \
                                                                stmt[d]['Liabilities']['Total liabilities'], \
                                                                stmt[d]['Liabilities']['TOTAL'])
                    stmt[d]['Liabilities']['Total Non-Current Liabilities'] = stmt[d]['Liabilities']['TOTAL']
                    del stmt[d]['Liabilities']['TOTAL']
                else:
                    print("%s: %r: Liabilities[TOTAL] is missing" %(stmt_type, d))
                    miss_count=1
        except Exception as E:
            print("correct_error(): %r: %r" %(stmt_type, d))
    #pretty_print(stmt)

    return stmt, miss_count


def update_US_fin_stmt_errors(collection, stk):
    if 'fig' not in stk.keys() and 'financial-statements' not in stk['fig'].keys():
        print("No financial figures available. Exiting percent calculation")
        return

    if 'balance-sheet' in stk['fig']['financial-statements'].keys():
        stk['fig']['financial-statements']['balance-sheet'], miss_count = \
            correct_error(stk['fig']['financial-statements']['balance-sheet'], 'balance-sheet')
        update_field(collection, stk['bscs']['symbol'], 'fig.financial-statements.balance-sheet', \
                                    stk['fig']['financial-statements']['balance-sheet'])
    return miss_count

# Update mongodb with Total Current Assets etc.
# During the regular update, they were overwritten by succeeding fields
# with same name.
# The idea is to substract Total Assets - Total Non current assets
# Likewise for other fields.
def update_all_US_fin_stmts_errors():
    db = open_db('Stocks')
    count=0

    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r: %r" %(i, stk['bscs']['symbol'], stk['bscs']['name']))
        miss_count = update_US_fin_stmt_errors(db.US_Stocks, copy.deepcopy(stk))
        count=count+miss_count

    print("Miss Count: %r" %(count))
    close_db()

