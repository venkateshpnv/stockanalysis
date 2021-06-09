import sys
import os
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
import pandas_datareader.data as data

import internet
import parse_html
from common import *
from datastructures import *
import conf
import hdf5
from hdf5 import *
import pandas_ta as ta
from io import StringIO

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

import talib

import random

num_cores = multiprocessing.cpu_count()
thread_factor = num_cores
#thread_factor=multiprocessing.cpu_count() * 8
technicals_ratelimit_reset_time = None

db_ips=['10.89.45.223', '10.89.45.152', '10.89.45.4']
def get_db_ip():
    #return random.choice(db_ips)
    return '10.89.45.241'

def check_mysql_replication_status(mysql_engine):
    return
    group_members = mysql_engine.execute('SELECT * FROM performance_schema.replication_group_members;')
    replicas = [[n for n in m] for m in group_members]
    
    if len(replicas) != len(db_ips):
        print("Some of the mysql nodes are down. Please check")
        sys.exit(1)
    
    for r in replicas:
        if 'ONLINE' not in r:
            print("%r is offline, please check" %(r))
            system.exit(1)
        if 'PRIMARY' not in r:
            print("%r is not primary, please check" %(r))
            sys.exit(1)

def open_sql_connection(ip=None, user='vpetla', passwd='petla123', port=3306, db=None):
    max_threads = thread_factor
    user = 'vpetla'
    passwd = 'petla123'
    if not ip or ip == '127.0.0.1' or ip =='localhost':
        ip = get_db_ip()

    try:
        mysql_engine = sqlalchemy.create_engine('mysql+pymysql://{0}:{1}@{2}:{3}'.format(user, passwd, ip, port), pool_size=max_threads)

        check_mysql_replication_status(mysql_engine)

        if db:
            existing_databases = mysql_engine.execute("SHOW DATABASES;")
            existing_databases = [d[0] for d in existing_databases]
            if db not in existing_databases:
                mysql_engine.execute("CREATE DATABASE {0}".format(db))
            #mysql_engine.execute("CREATE DATABASE IF NOT EXISTS {0}".format(db))
            close_sql_connection(mysql_engine)
            mysql_engine = sqlalchemy.create_engine('mysql+pymysql://{0}:{1}@{2}:{3}/{4}'.format(user, passwd, ip, port, db), pool_size=max_threads)

    except Exception as E:
        print("%r" %(str(E)))
        sys.exit(1)
    return mysql_engine

def close_sql_connection(mysql_engine):
    mysql_engine.dispose()

def db_name(mysql_engine):
    return str(mysql_engine.url).split('/')[-1]

def read_from_sql(query, mysql_engine, date=True):
    df = pd.DataFrame()
    df = pd.read_sql_query(query, mysql_engine)
    if date and not df.empty:
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
    check_mysql_replication_status(mysql_engine)
    try:
        df.to_sql(name=table,con=mysql_engine,index=False,if_exists='append')
    except Exception as E:
        print("DB.py: write_to_sql(), table: %r, exception: %r" %(table, str(E)))

def mysql_exists_table(mysql_engine, table_name):
    return mysql_engine.has_table(table_name)
    #query = 'show tables like %r;' %(table_name)
    #output= mysql_engine.execute(query)
    ##If table does not exist
    #if output.first() is None:
    #    return False
    #return True

def mysql_check_n_create_table(mysql_engine, table_name, unknown_table=False, primary_key=True, empty_table=False, fin_table=False):
    if not mysql_exists_table(mysql_engine, table_name):
        print("Creating table: %r" %(table_name))
        #query = 'create table '+ table_name + ' like test2;'
        #mysql_engine.execute(query)
        ##query = 'alter table ' + table +' add index(Date);'
        ##mysql_engine.execute(query)
        # Only add Symbol column
        if empty_table:
                query = 'create table '+ table_name + ' (`Symbol` varchar(12) NOT NULL, PRIMARY KEY(`Symbol`))'
        elif unknown_table:
            if primary_key:
                query = 'create table '+ table_name + ' (`Symbol` varchar(12) NOT NULL, `Date` varchar(12) NOT NULL, PRIMARY KEY(`Symbol`, `Date`))'
            else:
                query = 'create table '+ table_name + ' (`row_id` INT UNSIGNED NOT NULL AUTO_INCREMENT, `Symbol` varchar(12) NOT NULL, `Date` varchar(12) NOT NULL, PRIMARY KEY(`row_id`))'
        elif fin_table:
                query = 'create table '+ table_name + ' (`Symbol` varchar(12) NOT NULL, `Date` varchar(12) NOT NULL, PRIMARY KEY(`Symbol`, `Date`))'
        else:
            if primary_key:
                query = 'create table '+ table_name + ' (`Date` varchar(12) NOT NULL, PRIMARY KEY(`Date`))'
            else:
                query = 'create table '+ table_name + ' (`row_id` INT UNSIGNED NOT NULL AUTO_INCREMENT, `Date` varchar(12) NOT NULL, PRIMARY KEY(`row_id`))'

        mysql_engine.execute(query)

def mysql_get_columns(table):
    c = [i[0] for i in table.columns.items()]
    return c

def mysql_get_columns_from_engine(mysql_engine, table_name):
    metadata = MetaData()
    table = Table(table_name, metadata, autoload=True, autoload_with=mysql_engine)
    cols  =  mysql_get_columns(table)
    del metadata
    del table
    return cols

def mysql_add_column(mysql_engine, table_name, col_name, col_dtype, remove_spaces=True):
    if remove_spaces:
        col_name = col_name.replace('- ','').replace(' ', '_')
    query = 'alter table %s add column `%s` %s' %(table_name, col_name, col_dtype)
    mysql_engine.execute(query)

def mysql_add_columns(mysql_engine, table_name, missing_cols, cols_type='price', remove_spaces=True):
    unknown_fields = 0
    all_fields = {**price_fields, **price_change_fields,\
                **fin_year_fields, **fin_quarter_fields, \
                **income_fields, **balance_fields, **cash_fields,\
                **generic_fields,}
    if cols_type == 'text':
        for c in sorted(missing_cols):
            c_dtype = 'text'
            print("%s: Text cols: %s: %s" %(table_name, c, c_dtype))
            mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
    else:
        for c in sorted(missing_cols):
            if c in all_fields.keys():
                c_dtype = all_fields[c]
            else:
                c_dtype = 'float'
            print("%s: Column: %s: %s" %(table_name, c, c_dtype))
            mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
 
    #if cols_type == 'price':
    #    for c in sorted(missing_cols):
    #        if c in price_fields:
    #            c_dtype = price_fields_datatypes[price_fields.index(c)]
    #            #mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
    #        elif c in price_change_fields:
    #            c_dtype = price_change_fields_datatypes[price_change_fields.index(c)]
    #            #mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
    #        elif c in fin_year_fields:
    #            c_dtype = fin_year_fields_datatypes[fin_year_fields.index(c)]
    #            #mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
    #        elif c in fin_quarter_fields:
    #            c_dtype = fin_quarter_fields_datatypes[fin_quarter_fields.index(c)]
    #            #mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
    #        elif c.lower() in list(map(lambda x: x.lower(), generic_fields)):
    #            c_dtype = generic_fields_datatypes[generic_fields.index(c)]
    #        else:
    #            c_dtype = 'float'
    #        print("%s: Price cols: %s: %s" %(table_name, c, c_dtype))
    #        mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
   #else:
    #    for c in sorted(missing_cols):
    #        #if 'Symbol'.lower() in c.lower() or 'Date'.lower() in c.lower() or 'SPLIT'.lower() in c.lower():
    #        #    c_dtype = 'varchar(12)'
    #        gen_fields = list(map(lambda x: x.lower(), generic_fields))
    #        if c.lower() in gen_fields:
    #            c_dtype = generic_fields_datatypes[gen_fields.index(c.lower())]
    #        else:
    #            c_dtype = 'float'
    #        print("%s: other columns: %s: %s" %(table_name, c, c_dtype))
    #        mysql_add_column(mysql_engine, table_name, c, c_dtype, remove_spaces)
    return unknown_fields # Use of unknown_fields is deprecated.

def mysql_update_table(mysql_engine, table_name, df, check=False, insert=False, unknown_table=False, cols_type='price', temp=False, date_column=True, format_columns=True, primary_key=True, empty_table=False, fin_table=False):
    if df.empty:
        return

    check_mysql_replication_status(mysql_engine)

    if date_column:
        if 'Date.1' in list(df.columns):
            df['Date']=df['Date.1']
            del df['Date.1']
        else:
            df['Date'] = df.index

    df = df.where(pd.notnull(df), None)
    try:
        metadata = MetaData()
        if check:
            mysql_check_n_create_table(mysql_engine, table_name, unknown_table, primary_key, empty_table, fin_table)
            table = Table(table_name, metadata, autoload=True, autoload_with=mysql_engine)
            raw_table_cols = mysql_get_columns(table)
            table_cols = []
            if format_columns:
                remove_spaces = True
                for c in raw_table_cols:
                    table_cols.append(c.replace('- ','').replace(' ', '_'))
            else:
                table_cols = raw_table_cols
                remove_spaces = False

            raw_df_cols = list(df.columns)
            df_cols = []
            if format_columns:
                for c in raw_df_cols:
                    df_cols.append(c.replace('- ','').replace(' ', '_'))
            else:
                df_cols = raw_df_cols

            #df_cols_lower = list(map(lambda x: x.lower(), df_cols))
            #table_cols_lower = list(map(lambda x: x.lower(), table_cols))
            #missing_cols = list(set(df_cols)-set(table_cols))
            missing_cols = list_difference(df_cols,table_cols)
            if len(missing_cols) > 0:
                print("Adding missing columns")
                miss = mysql_add_columns(mysql_engine, table_name, missing_cols, cols_type, remove_spaces)
                if miss > 0:
                    PRINT_ERR("Failed to add %r columns to table %r" %(miss, table_name))
                    PRINT_ERR("Columns: ",missing_cols)
                    sys.exit(1)

                # Read the table again as the new columns have been added.
                del metadata
                del table
                metadata = MetaData()
                table = Table(table_name, metadata, autoload=True, autoload_with=mysql_engine)
        else:
            table = Table(table_name, metadata, autoload=True, autoload_with=mysql_engine)

        if temp:
            df.to_sql(name=table_name,con=mysql_engine,index=False,if_exists='append')
        else:
            conn  = mysql_engine.connect()
            for index, d in df.iterrows():
                items = {}
                key = str(pd.to_datetime(index).date())
                for k in d.keys().to_list(): #Skip date, date.1
                    if d[k] != None and not pd.isnull(d[k]):
                        if 'date' in k.lower():# == 'Date':
                            items[k]=str(d[k]).split(' ')[0]
                        else:
                            items[k]=d[k]
                    # TODO: Handle on conflict

                # If you are sure that this is the new record
                if insert:
                    stmt=table.insert().values(items)
                else:
                    # check if the key exists. If so, update the record,
                    # else create a new record.
                    stmt = select([table]).where(table.c.Date == key)
                    records = conn.execute(stmt).fetchall()
                    if len(records) == 0:
                        stmt=table.insert().values(items)
                    else:
                        if 'Date' in items.keys():
                            del items['Date']
                            # No items to insert, go to next row
                            if len(items) == 0:
                                continue
                        stmt=table.update().where(table.c.Date==key).values(items)
                        # table.c.keys() -> prints the list of all columns in the table.

                    #stmt=table.update().where(table.c.Date==key).values(items)
                try:
                    conn.execute(stmt)
                except Exception as E:
                    print("mysql update table: %r" %(str(E)))
                    pass
    finally:
        del metadata
        del table
        #conn.close()

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

    check_mysql_replication_status(engine)
    query = 'show tables like %r;' %(table)
    output= engine.execute(query)
    #If table does not exist
    if output.rowcount == 0:
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


    try:
        query = 'select * from '+ table
        #query = 'select * from '+ table + ' where Symbol=%r' %(table)
        rdf = pd.read_sql_query(query, engine)
    except (sqlalchemy.exc.ProgrammingError) as E:
        query = 'create table '+ table + ' like test2;'
        engine.execute(query)
        query = 'select * from '+ table
        rdf   = pd.read_sql_query(query, engine)

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
    return 'STK'+symbol.replace('.','_').replace('-','_')

def get_formatted_symbol(symbol):
    return symbol.replace('.','_').replace('-','_')

def get_symbols_from_mongo(collection=None, country='US'):
    if not collection:
        c = open_db_client()
        db = c['Stocks']

    collection = get_collection(country, db)
    symbols=collection.distinct("bscs.symbol")

    if not collection:
        close_db_client(c)

    return sorted(symbols)

def get_symbols_names_from_mongo(collection=None, country='US'):
    if not collection:
        c = open_db_client()
        db = c['Stocks']

    collection = get_collection(country, db)
    items = collection.find({},{'bscs.symbol':1,'bscs.name':1,'_id':0})
    if not collection:
        close_db_client(c)

    stocks = []
    for i in items:
        stocks.append("{}              {}".format(i['bscs']['symbol'], i['bscs']['name']))

    return stocks


# Fetch a stock data from mongodb
def read_stock_from_mongo(symbol):
    c  = open_db_client()
    db = c['Stocks']
    stocks = db.US_Stocks.find({'bscs.symbol':symbol}, no_cursor_timeout=True)
    close_db_client(c)
    if stocks.count() == 1:
        return stocks[0]
    return None

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

def get_symbols_from_sql2():
    engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Data')

    query='select distinct Symbol from US_All_Stocks_List' 
    rdf=pd.read_sql_query(query, engine)
    close_sql_connection(engine)

    if not rdf.empty:
        symbols = list(rdf['Symbol'])
    return symbols

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
        if not t.startswith('STK') and t not in other_tables:
            print("Renaming table: %r" %(t))
            rename_table(engine, t)

    symbols = [t.split('STK',1)[-1].replace('_', '.')  for t in tables if t.startswith('STK')]
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
mongodb_ip='10.89.45.49'
mongodb_port='27017'
def get_mongodb_connection_phrase():
    return 'mongodb://'+mongodb_ip+':'+mongodb_port

########################### MongoDB Related Calls ########3###################
def open_db(db_name):
    global client
    client = pymongo.MongoClient(get_mongodb_connection_phrase(), thread_factor)
    #client = pymongo.MongoClient("mongodb://localhost:27017/", thread_factor)
    #print("Opening: %r" %(client))
    db = client[db_name]
    return db

def open_db_client():
    c = pymongo.MongoClient(get_mongodb_connection_phrase(), thread_factor)
    #c = pymongo.MongoClient("mongodb://localhost:27017/", thread_factor)
    return c 

def close_db():
    global client
    #print("Closing: %r" %(client))
    client.close()

def close_db_client(c):
    c.close()

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
 
# This function is to fix the issue with the YahooFinance.
# Sometimes, it returns wrong volume information for the present date.
# Especially for the indices.
def check_volume_of_last_record(mysql_engine, table_name):
    columns = mysql_get_columns_from_engine(mysql_engine, table_name)
    if 'Volume' not in columns:
        return
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

def get_stock_prices(symbol, columns=None):
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    df = read_from_sql2(mysql_engine, 'STK'+symbol, columns)
    close_sql_connection(mysql_engine)

    return df
def get_fin_stmts(symbol, stmt_type, duration):
    columns = stmt_type + '_fields'
    exec("columns = %s" %(columns))
    if duration == 'quart':
        table = stmt_type + '_quart_table'
    else:
        table = stmt_type + '_table'
    exec("table = %s" %(table))

    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')
    df = read_from_sql2(mysql_engine, table, columns)
    close_sql_connection(mysql_engine)

    return df

def get_index_prices(country):
    indices_prices = {}
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    for k in US_indices.keys():
        query = 'select Date, `Adj Close`, `Day Change` from STK{} order by Date desc limit 1;'.format(US_indices[k])
        output = pd.read_sql_query(query, mysql_engine)
        indices_prices[US_indices[k]] = { 
                                        'price'  : output.iloc[0]['Adj Close'],
                                        'change' : output.iloc[0]['Day Change'],
                                        }

    close_sql_connection(mysql_engine)
    return indices_prices

def ignore_stock(stk):
    #if 'trading' in stk['bscs'].keys():
    #    if stk['bscs']['trading'] == 'NO' or stk['bscs']['trading'] == 'No':
    #        return True
    if 'ignore' in stk.keys():
        if stk['ignore'] == 'YES' or stk['ignore'] == 'Yes':
            return True
    return False

def update_since_dataframe(mysql_engine, table_name, collection, stk):
    #df = hdf5.get_dataframe(country, stk['bscs']['symbol'])
    #df = hdf5.read_from_hdf(country, stk['bscs']['symbol'])
    query = 'select Date, `Adj Close` from {} order by Date asc limit 1'.format(table_name)
    df = read_from_sql(query, mysql_engine)
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
    c  = open_db_client()
    db = c['Stocks']
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

    close_db_client(c)

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
    c  = open_db_client()
    db = c['Stocks']
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

    close_db_client(c)

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

# This function performs the whole set of operations for
# fetching the data related to a stock.
# It includes financial data, eps, split, divident history, prices,
# stock profile and other information.
# It updates the mongodb and the mysql db with all these information.
# This function can handle a new company listing and update all the info
# for an existing company.
def build_US_stock_complete_info(db, mysql_fin_engine, mysql_engine, symbol, symbols=None, sem=None):
    symbol = symbol.replace("^", "-").lstrip().rstrip()
    symbol = symbol.replace("~", "")
    symbol = symbol.replace("?", "")
 
    stocks_list = db.US_Stocks_List.find({'symbol':symbol},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    stocks = db.US_Stocks.find({'bscs.symbol':symbol}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    # Currently ignore if there is no entry in US_Stocks_List.
    # We will see how to handle it in future.
    # As of now, even though we ignore here, this should be taken care by
    # US_new_listings.py when it updates the new symbol information every week.
    if stocks_list.count() == 0:
        return

    # New stock
    if stocks.count() == 0:
        stk = {}
        # Initialize stock, populate financial data and update stock profile
        #remove_dir('/home/vpetla/work/stockanalysis/US_Stocks/html_pages')
        #create_dir('/home/vpetla/work/stockanalysis/US_Stocks/html_pages')
        build_US_stock_information(stocks_list[0])
        stocks = db.US_Stocks.find({'bscs.symbol':symbol}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        stk = stocks[0]
        set_sno('US')
    # Stock entry already exists
    else: 
        stk = stocks[0]
        # Populate financial data
        update_US_stock_information(db.US_Stocks, stk)
        ## Update stock profile
        #url = 'https://www.barchart.com/stocks/quotes/%s/profile' %(symbol)
        #html_text=internet.get_webpage(url)
        #update_US_stk_profile(html_text, db.US_Stocks)
 
    ## Update financial data percent change
    update_US_fin_percent_change(mysql_fin_engine, stk, 'fig')
    update_US_fin_percent_change(mysql_fin_engine, stk, 'quart_fig')

    if symbols is None:
        symbols = get_symbols_from_sql('US', mysql_engine)

    ## Update price and price change
    #hdf5.update_dataframe_price_volume('US', db, mysql_engine, symbol, symbols, stk, None, vpn_event=None)
    internet.update_price_change('US', db.US_Stocks, symbol, None, mysql_engine)

    ## Update stocks bscs
    update_stk_bscs_db('US', db, mysql_engine, stk, sem=None, lock=None, vpn_event=None)
   
    # Update betas
    #update_stock_betas('US', db.US_Stocks, mysql_engine, stk)

    # Populate/Update EPS, Dividend and Split History
    internet.populate_US_EPS(stk)
    
    if sem:
        sem.release()

def build_US_all_stock_complete_info():
    mysql_fin_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    c = open_db_client()
    db = c['Stocks']
    sem = threading.BoundedSemaphore(4)
    i = 0
    symbols = get_symbols_from_sql('US', mysql_engine)
    docs = db.US_Stocks.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #docs = db.US_Stocks.find({"bscs.dii_stake":{"$exists":False}},no_cursor_timeout=True)
    print("count: %r" %(docs.count()))
    for doc in docs:
        if i > -1:
        #if i > -1: # and not doc['bscs']['price']:
            sym = doc['bscs']['symbol']
            print("%d: %s: %s" %(i, sym, doc['bscs']['name']))
            sem.acquire()
            threading.Thread(target=build_US_stock_complete_info, args=(db, mysql_fin_engine, mysql_engine, sym, symbols, sem)).start()
            #build_US_stock_complete_info(db, mysql_fin_engine, mysql_engine, sym, symbols, sem)
        i = i + 1

    close_db_client(c)
    close_sql_connection(mysql_engine)
    close_sql_connection(mysql_fin_engine)

def update_US_all_stk_profile():
    c   = open_db_client()
    db  = c['Stocks']
    col = db['US_Stocks']
    i = 0
    docs = db.US_Stocks.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #docs = db.US_Stocks.find({"bscs.dii_stake":{"$exists":False}},no_cursor_timeout=True)
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
    close_db_client(c)

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
    
    #val = internet.get_LTP('US', symbol)
    #collection.update({'bscs.symbol': symbol}, {'$set': {"bscs.price": val}})

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
    c  = open_db_client()
    db = c['Stocks']
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

    close_db_client(c)

def update_db_price_volume(collection, stk):
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.price": to_float(stk['bscs']['price'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.volume": to_int(stk['bscs']['volume'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.mcap": to_float(stk['bscs']['mcap'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.outstanding_shares": to_int(stk['bscs']['outstanding_shares'])}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.type": stk['bscs']['type']}})
    collection.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"General.Exchange": stk['bscs']['exchange']}})
    #update_field(collection, stk['bscs']['symbol'], "dates.price_date", dt.now())

j=0

def update_bond_yields(sql_engine):
    table = 'BOND_YIELDS'
    mysql_check_n_create_table(sql_engine, table)
    query='select Date from ' + table + ' order by Date DESC limit 1'
    rdf = read_from_sql(query, sql_engine)
    if rdf.empty:
        url = treasury_yield_urls['whole']
    else:
        start = dt.strptime(rdf['Date'][0], "%Y-%m-%d").date()
        now = dt.now().date()
        if now.year != start.year:
            url = treasury_yield_urls['whole']
        elif now.month != start.month:
            url = treasury_yield_urls['year']
            url = url.rsplit('=',1)[0] + '=' + str(now.year)
        else:
            url = treasury_yield_urls['month']
            

    page = internet.get_webpage(url)
    df = pd.read_html(page)
    df = df[1]
    if not df.empty:
        df['Date'] = pd.to_datetime(df['Date'])
        df['Date'] = df['Date'].astype('str')
        df.index = df['Date']
        if not rdf.empty and rdf['Date'][0] in list(df.index):
            index = df.index.get_loc(rdf['Date'][0])
            df = df[index+1:]

    #mysql_update_table(sql_engine, table, df, insert=True)

    mysql_update_table(sql_engine, table, df, check=True, insert=True, unknown_table=False, cols_type='values', temp=False, date_column=False, format_columns=False, primary_key=True)

def fork_db_process(country, sem, lock, vpn_event=None):
    c = open_db_client()
    db = c['Stocks']
    sql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    t = None

    collection = get_collection(country, db)
    num_docs = collection.find({}).count()
    if num_docs == 0:
        return

    num_processes = 6 #* 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    i=0
    proxy=True

    try:
        symbols = get_symbols_from_sql(country, sql_engine)

        #update_bond_yields(sql_engine)

        today=str(dt.now().date())

        if country == 'India':
            indices = India_indices
        else:
            indices = US_indices 
 
        ###Indices
        #for k in indices.keys():
        #    stk = {}
        #    stk['bscs']={}
        #    stk['bscs']['symbol'] = k
        #    stk['bscs']['name'] = indices[k]
        #    sem.acquire()
        #    print(stk)
        #    update_stk_bscs_db(country, None, None, stk, 0, sem, lock, vpn_event, proxy=proxy, symbols=symbols)
        #    #processes[i%num_processes] = multiprocessing.Process(target=update_stk_bscs_db, args=(country, None, None, copy.deepcopy(stk), i%num_cores, sem, lock, vpn_event, proxy, symbols))
        #    #processes[i%num_processes].start()

        #Randomly get all records whose price is not updated till today
        #pipeline = [{'$sample': {'size':num_docs}},
        #            {'$match' : {"dates.price_date": {'$ne':today}}},
        #            #{"$group": {"_id": _id, "count": {"$sum":1}}},
        #            #{"$group": {"_id": None, "total": {"$sum": 1}, "details":{"$push":{"groupby": "$_id", "count": "$count"}}}}
        #            ]

        #stocks = db.US_Stocks.aggregate(pipeline, allowDiskUse=True).batch_size(10)
        #stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        #stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",order]])
        #stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["bscs.price_failcount",-1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({'dates.price_date':{'$lte': dt.now() - timedelta(1)}}).batch_size(10).sort([["dates.price_date",1]]).allow_disk_use(True)
        till_date = dt.combine(dt.now(), dt.min.time()) 
        #stocks = db.US_Stocks.find({'dates.price_date':{'$lt': till_date}}).batch_size(10).sort([["dates.price_date",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({}).batch_size(10).sort([["dates.price_date",1]]).allow_disk_use(True)
        stocks = db.US_Stocks.find({'bscs.symbol':'SOCL'}).batch_size(10)
        #stocks = db.US_Stocks.find({'bscs.price_failcount': {'$eq': 0}}).batch_size(10).sort([["dates.price_date",-1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$or" : [{'dates.price_date':{'$lt': till_date}}, {'bscs.price_failcount': {'$gt': 0}}]}).batch_size(10).sort([["dates.price_date",-1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and" : [{'dates.price_date':{'$lt': till_date}}, {'bscs.price_failcount': {'$eq': 0}}]}).batch_size(10).sort([["dates.price_date",-1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({'bscs.price_failcount': {'$lt': 10}}).batch_size(10).sort([["sno",-1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and" : [{'General.Type' : {'$ne': 'INDEX'}}, {'dates.price_date':{'$lt': till_date}}, {'bscs.price_failcount': {'$lt': 10}}]}).batch_size(10).sort([["bscs.price_failcount",1]]).allow_disk_use(True).sort([["General.Type",1]]).allow_disk_use(True)

        print("Total stocks: %r" %(stocks.count()))
   
        if dt.now().day % 2 == 0:
            order = 1
        else:
            order = -1
     
        for stk in stocks:
            with open('stop.txt', 'r') as f:
                data = f.read()

            if data == 'yes\n':
                break

            ##if ignore_stock(stk):
            ##    continue
            ##print("DB: %d: %s: %s"%(i,stk['bscs']['symbol'],stk['bscs']['name']))
            #if 'price_failcount' in stk['bscs'].keys() and stk['bscs']['price_failcount'] > 10:
            #    print("price_Failcount: %d, Skipping: %r" %(stk['bscs']['price_failcount'], stk['bscs']['symbol']))
            #    continue

            #if vpn_event:
            #    while vpn_event.is_set() is False:
            #        time.sleep(2)
            #        continue
            if vpn_event and vpn_event.is_set() is False:
                vpn_event.wait()

            sem.acquire()
            if 'name' in stk['bscs'].keys():
                print("DB: %d: %s: %s"%(i,stk['bscs']['symbol'],stk['bscs']['name']))
            else:
                print("DB: %d: %s: %s"%(i,stk['bscs']['symbol'],stk['bscs']['longName']))
            #update_stk_bscs_db(country, db, sql_engine, stk, sem, lock, vpn_event, proxy=proxy, symbols=symbols)
            #t = threading.Thread(target=update_stk_bscs_db, args=(country, db, sql_engine, copy.deepcopy(stk), sem, lock, vpn_event, proxy, symbols))
            #t.start()

            #update_stk_bscs_db(country, None, None, stk, 0, sem, lock, vpn_event, proxy=proxy, symbols=symbols)
            processes[i%num_processes] = multiprocessing.Process(target=update_stk_bscs_db, args=(country, None, None, copy.deepcopy(stk), i%num_cores, sem, lock, vpn_event, proxy, symbols))
            processes[i%num_processes].start()
            #t = threading.Thread(target=update_stk_bscs_db, args=(country, db, sql_engine, copy.deepcopy(stk), sem, lock, vpn_event, proxy, symbols))
            #t.start()
            i = i + 1
            #break
    finally:
        # Wait till all threads are completed. You can use join() instead.
        # But need to track threads and update variables.
        # Simplest way is to wait for tentative time taken for the end threads to complete
        # Randomly estimated it to be 10 sec and it perfectly works.
        #while threading.active_count() > 0:
        #    print("Waiting for all threads  %r to join" %(threading.active_count()))
        #    time.sleep(5)
        #    continue
        #if t:
        #    t.join()
        #time.sleep(60)
        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()
 
        close_db_client(c)
        close_sql_connection(sql_engine)
    print("DB Process Stocks tried :%r"%(i))

def fork_hdf5_process(country, sem, vpn_event=None, eod_token=True):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    sql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

    f = open("/home/vpetla/work/stockanalysis/get_price_fails.txt", "w")
    f.close()
    sort = [1, -1][dt.now().day % 2 == 0]

    today = dt.combine(dt.now(), dt.min.time())
    num_docs = collection.find({}).count()
    #num_docs = collection.find({"dates.mysql_price_date": {'$ne':today}})
    if num_docs == 0:
        close_db_client(c)
        close_sql_connection(sql_engine)
        return

    num_processes = num_cores * 2
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    eod_token = True
    i=0
 
    #symbols = hdf5.get_symbols_hdf_store(country)
    #symbols = hdf5.get_symbols_from_hdf(country)
    symbols = get_symbols_from_sql(country, sql_engine)
    #symbols = get_symbols_from_mongo(collection)
    
    if country == 'India':
        indices = India_indices
    else:
        indices = US_indices 

    try:
        if dt.now().day % 2 == 0:
            order = 1
        else:
            order = -1
 
        #Update Indices First
        for k in indices.keys():
            stk = {}
            stk['bscs']={}
            stk['bscs']['symbol'] = k
            stk['bscs']['name'] = indices[k]
            stk['bscs']['quoteType'] = 'Index'
            stk['sno'] = i
            sem.acquire()
            hdf5.update_dataframe_price_volume(country, db, sql_engine, stk['bscs']['symbol'], symbols, stk, 0, sem, vpn_event, eod_token=True)
            #processes[i%num_processes] = multiprocessing.Process(target=update_dataframe_price_volume, args=(country, None, None, stk['bscs']['symbol'], symbols, copy.deepcopy(stk), i%num_cores, sem, vpn_event, eod_token))
            #processes[i%num_processes].start()
            i = i + 1

        # Get the data in bulk mode for all the stocks in a single API call and update the database.
        # This will be much quicker than pulling data for the each stock.
        # This call does the data update for all the stocks having the price data till the previous trading day.
        #if eod_token is True:
        #    hdf5.bulk_update_price_volume(country, db, sql_engine)
 
        # As the bulk mode would have updated most of the stocks, now update the remaining stocks.
        # They include 
        # 1. New stocks
        # 2. Stocks that are not updated for sometime.
        #stocks = db.US_Stocks.find({"$and":[{"dates.mysql_price_date": {"$exists": False }}, {'General.Exchange':{"$in":major_exchanges}]}).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",1]]).allow_disk_use(True)
        #print("Total new stocks: %r" %(stocks.count()))
        ##stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        #for stk in stocks:
        #    #print("%d: Mysql: Checking: %r" %(i, stk['bscs']['symbol']))
        #    sem.acquire()
        #    #hdf5.update_dataframe_price_volume(country, db, sql_engine, stk['bscs']['symbol'], symbols, stk, 0, sem, vpn_event, eod_token=True)
        #    processes[i%num_processes] = multiprocessing.Process(target=update_dataframe_price_volume, args=(country, None, None, stk['bscs']['symbol'], symbols, copy.deepcopy(stk), i%num_cores, sem, vpn_event, eod_token))
        #    processes[i%num_processes].start()
        #    i = i + 1


        #stocks = db.US_Stocks.find({"$and" : [{"$or": [{"dates.mysql_price_date": {"$exists": False }}, {"$and":[{"dates.mysql_price_date": {"$lt": get_latest_trading_day()}}, {"General.IsDelisted": False}]}]}, {'General.Type':'Common Stock'}, {'General.Exchange':{"$in":major_exchanges}}]}).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",1]]).allow_disk_use(True)
        stocks = db.US_Stocks.find({"$and" : [ \
                                                {"$or": [\
                                                            {"dates.mysql_price_date": {"$exists": False }},\
                                                            {"dates.mysql_price_date": {"$lt": get_latest_trading_day()}}\
                                                        ]\
                                                },\
                                                {"General.IsDelisted": False},\
                                                {'General.Type':'Common Stock'},\
                                                {'General.Exchange':{"$in":major_exchanges}},\
                                                {'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}}\
                                            ]\
                                    }\
                                    ).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",sort]]).allow_disk_use(True)
        #stocks=db.US_Stocks.find({"$and":[{'General.Exchange':{"$in":major_exchanges}}, {'General.Type':'Common Stock'}]}).batch_size(10).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = collection.find({'bscs.symbol':'CRHM'},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        print("Total stocks: %r" %(stocks.count()))
        for stk in stocks:
            #print("%d: Mysql: Checking: %r" %(i, stk['bscs']['symbol']))
            sem.acquire()
            #hdf5.update_dataframe_price_volume(country, db, sql_engine, stk['bscs']['symbol'], symbols, stk, 0, sem, vpn_event, eod_token=True)
            processes[i%num_processes] = multiprocessing.Process(target=update_dataframe_price_volume, args=(country, None, None, stk['bscs']['symbol'], symbols, copy.deepcopy(stk), i%num_cores, sem, vpn_event, eod_token))
            processes[i%num_processes].start()
            i = i + 1

    finally:
        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()
 
        time.sleep(15)
        close_db_client(c)
        close_sql_connection(sql_engine)
    print("HDF5 Stocks tried :%r"%(i))

def update_price_failcount(stk, country, df=False):
    failcount = 1
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    if df:
        price_failcount='mysql_price_failcount'
        field = 'failcount.mysql_price_failcount'
    else:
        price_failcount='price_failcount'
        field = 'failcount.price_failcount'

    if 'bscs' in stk.keys() and price_failcount in stk['bscs'].keys():
        failcount = failcount + stk['bscs'][price_failcount]
   
    print("%s: Updating %s for field %s" %(stk['bscs']['symbol'], failcount, field))
    update_field(collection, stk['bscs']['symbol'], field, failcount)
    
    # Ignore the stk for future purposes if failed to get data
    # for more than 10 times.
    if failcount > 10:
        if 'trading' not in stk['bscs'].keys():
            update_field(collection, stk['bscs']['symbol'], "bscs.trading", "NO")
            update_field(collection, stk['bscs']['symbol'], "bscs.trading_stop_date", str(dt.now().date()))
        elif stk['bscs']['trading'] == 'Yes' or stk['bscs']['trading'] == 'YES':
            update_field(collection, stk['bscs']['symbol'], "bscs.trading", "NO")
            update_field(collection, stk['bscs']['symbol'], "bscs.trading_stop_date", str(dt.now().date()))
 
# Update price, mcap, volume etc
def update_stk_bscs_db(country, db, mysql_engine, stk, core, sem, lock, vpn_event, proxy=False, symbols=None):
    global j
    failcount=1

    aff = 0 | 1 << core
    #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
    #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))
 
    try:
        if not db:
            c = open_db_client()
            db = c['Stocks']
        if not mysql_engine:
            mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks')

        today=str(dt.now().date())
        symbol = stk['bscs']['symbol'].replace('.','-')
        if not symbols:
            symbols = get_symbols_from_sql2()

        retries = 1
        conn_retries = 0
        info_retries = 0
        info = None
        share_df = None
        puts_volume = 0
        calls_volume = 0
        puts_open_interest_volume = 0
        calls_open_interest_volume = 0
        put_call_ratio = 0
        put_call_open_interest_ratio = 0
        puts = pd.DataFrame()
        calls = pd.DataFrame()
        df = pd.DataFrame()
        share_df_flag=True

        while True:
            try:
                if vpn_event and vpn_event.is_set() is False:
                    print("**** %s: Waiting..  VPN is changing" %(symbol))
                    vpn_event.wait()
                    print("**** %s: Waking up" %(symbol))
    
                if country == 'US':
                    if info_retries > 5:
                        print("Failed to get info for %s. Returning None" %(symbol))
                        return None
                    tick = internet.get_ticker(symbol)
                    if not info:
                        if proxy:
                            proxy_server = get_proxy()
                            print("info: proxy_server: %s" %(proxy_server))
                            try:
                                info = tick.get_info(proxy=proxy_server)
                            except requests.exceptions.ProxyError as E:
                                PRINT_ERR("DB.py: %s: %s:  tick.get_info() Proxy Error, retrying" %(symbol, proxy_server))
                                info_retries = info_retries + 1
                                continue
                            #except urllib.error.HTTPError as E:
                            except requests.exceptions.HTTPError as E:
                                print("%s: %s" %(symbol, E))
                                info_retries = info_retries + 1
                            except Exception as E:
                                print("DB.py: %s: (%s) error for bscs info" %(symbol, E))
                                info = data.get_quote_yahoo(symbol)
                                if not info.empty:
                                    info = info.to_dict('index')
                                    info = info[symbol]
                                    del info['language']
                                else:
                                    info = None

                            try:
                                share_df = tick.major_holders
                            except Exception as E:
                                print("DB.py: %s: (%s) error for Major Holders" %(symbol, E))
                                share_df = None


                        else:
                            try:
                                info = tick.get_info()
                            #except KeyError as E:
                            except Exception as E:
                                print("DB.py: %s: (%s) error for bscs info" %(symbol, E))
                                info = None

                            try:
                                share_df = tick.major_holders
                            except Exception as E:
                                print("DB.py: %s: (%s) error for Major Holders" %(symbol, E))
                                share_df = None

                    ret, df = internet.get_stock_price_data(country, tick, symbol, symbols, stk, db, mysql_engine, proxy, vpn_event, write_to_db=False)
                    if ret:
                        print("DB.py: %s: df success, len(df): %r" %(symbol, len(df)))

                    # No puts, calls for index
                    if info and info['quoteType'] == 'INDEX':
                        break

                    if not df.empty:

                        # The output can be of two types.
                        # Number 1:
                        # Add share holders information.
                        # The share_df will be something like below.
                        # 0  13.04%        % of Shares Held by All Insider
                        # 1  12.53%       % of Shares Held by Institutions
                        # 2  14.41%        % of Float Held by Institutions
                        # 3     178  Number of Institutions Holding Shares
                        #
                        # Number 2:
                        #                                        Holder  Shares Date Reported  % Out       Value
                        #         Price (T.Rowe) Associates Inc  58431388  Sep 29, 2020         9.64%  1810788714
                        #                              FMR, LLC  31279728  Sep 29, 2020         5.16%   969358770
                        #  Massachusetts Financial Services Co.  27462685  Sep 29, 2020         4.53%   851068608
                        #             Select Equity Group, Inc.  26146255  Sep 29, 2020         4.31%   810272442
                        #               D1 Capital Partners, LP   9519618  Sep 29, 2020         1.57%   295012961
                        #    Champlain Investment Partners, LLC   7982625  Sep 29, 2020         1.32%   247381548
                        #             Janus Henderson Group PLC   6802256  Sep 29, 2020         1.12%   210801913
                        #                            BAMCO Inc.   6499216  Sep 29, 2020         1.07%   201410703
                        #  Artisan Partners Limited Partnership   6234197  Sep 29, 2020         1.03%   193197765
                        #   Bank Of New York Mellon Corporation   6213664  Sep 29, 2020         1.03%   192561447

                        if info and info['quoteType'] != 'ETF' and share_df is not None and not share_df.empty:
                            if 'Holder' in share_df.columns:
                                df.ix[-1, 'percent_insider'] = None
                                df.ix[-1, 'percent_institution'] = sum([float(d['% Out'].split('%')[0]) for i, d in share_df.iterrows()])
                                df.ix[-1, 'float_percent_institution'] = None
                                df.ix[-1, 'num_institutions'] = len(share_df.index)
                            else:
                                try:
                                    for i in range(len(tick_share_holders)-1):
                                        df.ix[-1, tick_share_holders[i]] = float(share_df.iloc[i][0].split("%")[0])/100 
                                    df.ix[-1, tick_share_holders[-1]] = share_df.iloc[-1][0]
                                except Exception as E:
                                    share_df_flag=False
                                    print("DB.py: Exception(%r):  share_df: %r " %(E, share_df))

                        # Add the fields like short ratio etc.
                        for i in range(len(tick_fields)):
                            if info and tick_fields[i] in info.keys():
                                df.ix[-1, tick_fields[i]] = info[tick_fields[i]]
                            else:
                                df.ix[-1, tick_fields[i]] = None

                        try:
                            options_chain = tick.option_chain()
                            puts  = options_chain.puts
                            calls = options_chain.calls
                            puts_volume  = sum(puts['volume'].dropna())
                            calls_volume = sum(calls['volume'].dropna())
                            puts_open_interest_volume  = sum(puts['openInterest'].dropna())
                            calls_open_interest_volume = sum(calls['openInterest'].dropna()) 
                        except IndexError as E:
                            print("%s: %s Index error for option chain" %(symbol, E))
                        except KeyError as E:
                            print("%s: %s Key error for option chain" %(symbol, E))

                        if calls_volume > 0:
                            put_call_ratio = puts_volume/calls_volume
                        else:
                            put_call_ratio = 0
                        if calls_open_interest_volume > 0:
                            put_call_open_interest_ratio = puts_open_interest_volume/calls_open_interest_volume
                        else:
                            put_call_open_interest_ratio = 0
                        df.ix[-1, 'puts_volume']  = puts_volume
                        df.ix[-1, 'calls_volume'] = calls_volume
                        df.ix[-1, 'puts_open_interest_volume']  = puts_volume
                        df.ix[-1, 'calls_open_interest_volume'] = calls_volume
                        df.ix[-1, 'put_call_ratio']               = put_call_ratio
                        df.ix[-1, 'put_call_open_interest_ratio'] = put_call_open_interest_ratio

                        df = df.where(pd.notnull(df), None)

                        if not puts.empty:
                            puts['Date'] = str(dt.now().date())
                            puts.index = puts['Date']
                            #del puts['Date']
                            #first_col = puts.pop('Date')
                            #puts.insert(0, 'Date', first_col)
                            puts_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Options_Puts')
    
                            mysql_check_n_create_table(puts_engine, get_symbol_table_name(symbol), unknown_table=False, primary_key=False)
                            query='select Date from ' + get_symbol_table_name(symbol) + ' where Date=%r' %(str(dt.now().date())) 
                            rdf = read_from_sql(query, puts_engine)
                            if rdf.empty:
                                query='select Date, row_id from ' + get_symbol_table_name(symbol) + ' order by row_id DESC LIMIT 1'
                                rdf = read_from_sql(query, puts_engine)
                                if rdf.empty:
                                    row_id_start = 1
                                else:
                                    row_id_start = rdf['row_id'][0] + 1
                                #puts.columns[0] = 'row_id'
                                puts.insert(0,'row_id',range(row_id_start, row_id_start+len(puts)))

                                mysql_update_table(puts_engine, get_symbol_table_name(symbol), puts, check=True, insert=True, unknown_table=False, cols_type='options', temp=False, date_column=False, format_columns=False, primary_key=False)
                            close_sql_connection(puts_engine)

                        if not calls.empty:
                            calls['Date'] = str(dt.now().date())
                            calls.index = calls['Date']
                            #del calls['Date']
                            #first_col = calls.pop('Date')
                            #calls.insert(0, 'Date', first_col)
                            calls_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Options_Calls')
    
                            mysql_check_n_create_table(calls_engine, get_symbol_table_name(symbol), unknown_table=False, primary_key=False)
                            query='select Date from ' + get_symbol_table_name(symbol) + ' where Date=%r' %(str(dt.now().date())) 
                            rdf = read_from_sql(query, calls_engine)
                            if rdf.empty:
                                query='select Date, row_id from ' + get_symbol_table_name(symbol) + ' order by row_id DESC LIMIT 1'
                                rdf = read_from_sql(query, calls_engine)
                                if rdf.empty:
                                    row_id_start = 1
                                else:
                                    row_id_start = rdf['row_id'][0] + 1
                                #puts.columns[0] = 'row_id'
                                calls.insert(0,'row_id',range(row_id_start, row_id_start+len(calls)))


                                mysql_update_table(calls_engine, get_symbol_table_name(symbol), calls, check=True, insert=True, unknown_table=False, cols_type='calls', temp=False, date_column=False, format_columns=False, primary_key=False)
                            close_sql_connection(calls_engine)

                    break
                else:
                    PRINT_ERR("Unknown Country Name")
                    return None
            except (KeyError, pdr._utils.RemoteDataError, IndexError) as E:
                PRINT_ERR("DB: %s:  Error, retrying, exception: %r" %(symbol, E))
                if vpn_event:
                    if retries  > 1:
                        PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
                        update_price_failcount(stk, country)
                        return None
                    if vpn_event.is_set() is False:
                        print("**** %s: 2DF: Waiting..  VPN is changing" %(symbol))
                        vpn_event.wait()
                        print("**** %s: 2DF: Waking up" %(symbol))
                        continue
                    else: 
                        time.sleep(5)
                        vpn_event.clear()
                        print("**** %s: VPN Changing: Sent Wait Event" %(symbol))
                        change_vpn()
                        vpn_event.set()
                        print("**** %s: VPN Changed: Sending Wakeup Event" %(symbol))
                        retries = retries + 1
                        continue
                else:
                    if retries  > 1:
                        PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
                        update_price_failcount(stk, country)
                        return None
                    retries = retries + 1
                    time.sleep(2)
                    continue
            #except (urllib3.exceptions.NewConnectionError, OpenSSL.SSL.SysCallError) as E:
            except Exception as E:
                if conn_retries > 1:
                    PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
                    return None
                PRINT_ERR("%s: DB.py: Connection Error, retrying, exception: %r" %(symbol, E))
                PRINT_ERR("%s: DB.py: Connection Error, retrying, exception: %r, df: %r, info: %r" %(symbol, E, df, info))
                time.sleep(1)
                conn_retries = conn_retries + 1
                continue
    
        collection = get_collection(country, db)

        # Update price change information
        if not df.empty:
            table = get_symbol_table_name(symbol)
            if len(symbols) == 0 or symbol.replace('-','.').replace('_','.') not in symbols:
                # Check if symbol is ending with +, =, -
                # Delete those junk symbols from mongodb
                if re.match(r'.*[\+|\=|\-]$', symbol):
                    print("Deleting Junk Symbol: %r" %(symbol))
                    db.US_Stocks.remove({"bscs.symbol" : symbol})
                    db.US_Stocks_List.remove({"symbol" : symbol})
                else:
                    if not df.empty:
                        print("mysql: %s: %s"%(symbol,stk['bscs']['name']))
                        check_n_write_to_sql(mysql_engine, table, copy.deepcopy(df), list(df.columns))
                        # Reset mysql_price_failcount
                        mysql_price_failcount = 0
     
                    else:
                        update_field(collection, stk['bscs']['symbol'], "ignore", "YES")
                        update_price_failcount(stk, country, df=True)
            else:
                mysql_update_table(mysql_engine, table, df, insert=True, check=True, format_columns=False)
                # Reset mysql_price_failcount
                mysql_price_failcount = 0
        else:
            if ret is False:
                if 'mysql_price_failcount' in stk['bscs'].keys():
                    mysql_price_failcount = stk['failcount']['mysql_price_failcount'] + 1
                else:
                    mysql_price_failcount = 1
            else:
                mysql_price_failcount = 0

        if info and info['quoteType'] == 'INDEX':
            # Dont worry, this is end up in finally: block
            return

        # Update bscs information
        if info:
            bscs = stk['bscs']
            stk['bscs'] = info
            stk['bscs']['symbol'] = bscs['symbol']

            # Reset price fail count
            stk['bscs']['price_fetch_success'] = 'YES'
            stk['failcount']['price_failcount'] = 0
            stk['bscs']['trading'] = "YES"
            stk['failcount']['mysql_price_failcount'] = mysql_price_failcount

            if info['quoteType'] != 'ETF' and share_df_flag and share_df is not None and not share_df.empty:
                try:
                    stk['bscs']['percent_insiders'] = float(share_df.iloc[0][0].split('%')[0])/100
                    stk['bscs']['percent_institutions'] = float(share_df.iloc[1][0].split('%')[0])/100
                    stk['bscs']['float_percent_institutions'] = float(share_df.iloc[2][0].split('%')[0])/100
                    stk['bscs']['number_of_institutions'] = share_df.iloc[3][0]
                except Exception as E:
                    pass
            else:
                if 'percent_insiders' in bscs.keys():
                    stk['bscs']['percent_insiders'] = bscs['percent_insiders'] 
                if 'percent_institutions' in bscs.keys():
                    stk['bscs']['percent_institutions'] = bscs['percent_institutions'] 
                if 'float_percent_institutions' in bscs.keys():
                    stk['bscs']['float_percent_institutions'] = bscs['float_percent_institutions'] 
                if 'number_of_institutions' in bscs.keys():
                    stk['bscs']['number_of_institutions'] = bscs['number_of_institutions']
            j = j + 1
        else:
            if not df.empty:
                stk['bscs']['regularMarketPrice'] = df.iloc[-1]['Adj Close']

            stk['bscs']['price_fetch_success'] = 'NO'
            if 'bscs' in stk.keys() and 'price_failcount' in stk['bscs'].keys():
                stk['bscs']['price_failcount'] = stk['bscs']['price_failcount'] + 1
            else:
                stk['bscs']['price_failcount'] = 1
            # Ignore the stk for future purposes if failed to get data
            # for more than 10 times.
            if failcount > 10:
                stk['bscs']['trading'] = "NO"
            update_field(collection, stk['bscs']['symbol'], "failcount.price_failcount", failcount)
            update_field(collection, stk['bscs']['symbol'], "dates.price_date", dt.combine(dt.now(), dt.min.time()))

        stk['dates']['price_date'] = dt.combine(dt.now(), dt.min.time())
        update_field(collection, stk['bscs']['symbol'], "bscs", stk['bscs'])
        update_field(collection, stk['bscs']['symbol'], "dates.mysql_price_date", dt.combine(dt.now(), dt.min.time()))

    finally:
        close_db_client(c)
        close_sql_connection(mysql_engine)
        if sem:
            sem.release()

def update_candlesticks(collection, sym, df):
    update_field(collection, sym, "technicals.candlesticks.TWOCROWS",float(talib.CDL2CROWS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THREECROWS",float(talib.CDL3BLACKCROWS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THREEINSIDE",float(talib.CDL3INSIDE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THREELINESTRIKE",float(talib.CDL3LINESTRIKE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THREEOUTSIDE",float(talib.CDL3OUTSIDE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THREESTARSINSOUTH",float(talib.CDL3STARSINSOUTH(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THREEWHITESOLDIERS",float(talib.CDL3WHITESOLDIERS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.ABANDONEDBABY",float(talib.CDLABANDONEDBABY(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.ADVANCEBLOCK",float(talib.CDLADVANCEBLOCK(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.BELTHOLD",float(talib.CDLBELTHOLD(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.BREAKAWAY",float(talib.CDLBREAKAWAY(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.CLOSINGMARUBOZU",float(talib.CDLCLOSINGMARUBOZU(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.CONCEALBABYSWALL",float(talib.CDLCONCEALBABYSWALL(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.COUNTERATTACK",float(talib.CDLCOUNTERATTACK(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.DARKCLOUDCOVER",float(talib.CDLDARKCLOUDCOVER(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.DOJI",float(talib.CDLDOJI(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.DOJISTAR",float(talib.CDLDOJISTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.DRAGONFLYDOJI",float(talib.CDLDRAGONFLYDOJI(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.ENGULFING",float(talib.CDLENGULFING(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.EVENINGDOJISTAR",float(talib.CDLEVENINGDOJISTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.EVENINGSTAR",float(talib.CDLEVENINGSTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.GAPSIDESIDEWHITE",float(talib.CDLGAPSIDESIDEWHITE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.GRAVESTONEDOJI",float(talib.CDLGRAVESTONEDOJI(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.HAMMER",float(talib.CDLHAMMER(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.HANGINGMAN",float(talib.CDLHANGINGMAN(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.HARAMI",float(talib.CDLHARAMI(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.HARAMICROSS",float(talib.CDLHARAMICROSS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1])) 
    update_field(collection, sym, "technicals.candlesticks.HIGHWAVE",float(talib.CDLHIGHWAVE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1])) 
    update_field(collection, sym, "technicals.candlesticks.HIKKAKE",float(talib.CDLHIKKAKE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.HIKKAKEMOD",float(talib.CDLHIKKAKEMOD(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.HOMINGPIGEON",float(talib.CDLHOMINGPIGEON(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.IDENTICAL3CROWS",float(talib.CDLIDENTICAL3CROWS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.INNECK",float(talib.CDLINNECK(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.INVERTEDHAMMER",float(talib.CDLINVERTEDHAMMER(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.KICKING",float(talib.CDLKICKING(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.KICKINGBYLENGTH",float(talib.CDLKICKINGBYLENGTH(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.LADDERBOTTOM",float(talib.CDLLADDERBOTTOM(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.LONGLEGGEDDOJI",float(talib.CDLLONGLEGGEDDOJI(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.LONGLINE",float(talib.CDLLONGLINE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.MARUBOZU",float(talib.CDLMARUBOZU(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.MATCHINGLOW",float(talib.CDLMATCHINGLOW(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.MATHOLD",float(talib.CDLMATHOLD(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.MORNINGDOJISTAR",float(talib.CDLMORNINGDOJISTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.MORNINGSTAR",float(talib.CDLMORNINGSTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.ONNECK",float(talib.CDLONNECK(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.PIERCING",float(talib.CDLPIERCING(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.RICKSHAWMAN",float(talib.CDLRICKSHAWMAN(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.RISEFALL3METHODS",float(talib.CDLRISEFALL3METHODS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1])) 
    update_field(collection, sym, "technicals.candlesticks.SEPARATINGLINES",float(talib.CDLSEPARATINGLINES(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.SHOOTINGSTAR",float(talib.CDLSHOOTINGSTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.SHORTLINE",float(talib.CDLSHORTLINE(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.SPINNINGTOP",float(talib.CDLSPINNINGTOP(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.STALLEDPATTERN",float(talib.CDLSTALLEDPATTERN(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.STICKSANDWICH",float(talib.CDLSTICKSANDWICH(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.TAKURI",float(talib.CDLTAKURI(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.TASUKIGAP",float(talib.CDLTASUKIGAP(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.THRUSTING",float(talib.CDLTHRUSTING(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.TRISTAR",float(talib.CDLTRISTAR(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.UNIQUE3RIVER",float(talib.CDLUNIQUE3RIVER(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.UPSIDEGAP2CROWS",float(talib.CDLUPSIDEGAP2CROWS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))
    update_field(collection, sym, "technicals.candlesticks.XSIDEGAP3METHODS",float(talib.CDLXSIDEGAP3METHODS(df['Open'],df['High'],df['Low'], df['Adj Close'])[-1]))

# Calculates estimated profit and returns the df back
def calculate_ep(df, val):
    ep0 = val
    def ep(row):
        nonlocal ep0
        epn = ep0 * (1 + row['pct_change'])
        ep0 = epn
        return epn
    df['ep'] = df.apply(ep, axis=1)
    return df

def calc_psar(df, duration=None):
    if duration:
        df = df.loc[df.index[-1]-duration:]

    psar = ta.psar(df['High'], df['Low'], df['Adj Close'],af=0.02)
    
    # Add price column to the psar
    psar['Adj Close'] = df['Adj Close']
    
    # Rename columns to simple names for easy reading
    new_cols={}
    new_cols['PSARl_0.02_0.2']='long';new_cols['PSARs_0.02_0.2']='short';new_cols['PSARaf_0.02_0.2']='af';new_cols['PSARr_0.02_0.2']='r'
    psar.rename(columns=new_cols, inplace=True)
    
    # Get the dates of switch between long and short positions of the stock
    # For example,
    #               long  short  Adj Close     af     r 
    #Date                                               
    #2020-10-02      NaN  11.41       9.20   0.02  True 
    #2020-10-26    8.900    NaN       9.95   0.06  True 
    #2020-12-01      NaN  33.50      25.67   0.20  True 
    #2020-12-22   21.150    NaN      28.04   0.04  True 
    #2021-02-02      NaN  45.00      31.02   0.08  True 
    #2021-03-10   20.180    NaN      24.75   0.16  True 
    #2021-03-23      NaN  27.47      23.26   0.08  True 
    #2021-04-09   20.860    NaN      24.04   0.08  True 
    #2021-04-19      NaN  26.20      21.94   0.08  True 
    #2021-05-18   17.055    NaN      21.24   0.12  True
    sw = psar[psar['r'] == True]
    
    # Start from first long position date
    sw = sw.loc[sw['long'].first_valid_index():]
    
    # Get the price percetange change during these dates
    sw.insert(loc=4, column='pct_change', value=sw['Adj Close'].pct_change())
    
    # Filter only the dates to sell and make profit
    sw = sw.loc[sw.short.notnull()]
    
    # Now we have dates and percentage changes where its ideal
    # to sell the stock and make profit.
    # Calculate profit achieved in the whole period.
    # Assume you start with an investment of $1
    start = 1
    sw['ep']=np.nan
    sw = calculate_ep(sw, 1) # Initial investment is $1
    return sw

def update_SAR_params(collection, sym, df):
    # Parabolic SAR
    # Exit the position if the SAR is greater than 'Adj Close'
    # Enter the position if the SAR is less than 'Adj Close'
    sar  = talib.SAR(df['High'], df['Low'])
    if len(sar.index) == 0:
        update_field(collection, sym, "technicals.sar", {})
    else:
        # Get the daily up/down SAR to Price trend information
        sar_trend = pd.DataFrame(np.where(sar < df['Adj Close'], "UP", "DOWN"), index=sar.index)

        # Take the today's trend
        # Findout the length of the trend.
        # For example if today's trend is UP, find out
        # the number of days since the UP trend in the price.
        trend = sar_trend.iloc[-1][0]
        days = 1
        for i, d in sar_trend.iloc[0:-1][::-1].iterrows():
            if trend == d[0]:
                days = days + 1
            else:
                break

        if trend == 'DOWN':
            days = -days

        update_field(collection, sym, "technicals.sar.trend", days)
        update_field(collection, sym, "technicals.sar.latest", sar.iloc[-1])

        #ep: estimated profit
        duration=relativedelta(years=1)
        sw = calc_psar(copy.deepcopy(df), duration)
        i = hdf5.get_nearest_index(df, (df.index[-1]-duration).to_pydatetime().date())
        change = percent_change(df.iloc[i]['Adj Close'], df['Adj Close'][-1])
        ep = np.nan
        alpha = np.nan
        if not sw['ep'].empty:
            ep = sw.ep[-1] - 1
            alpha = percent_change(change, ep)
        update_field(collection, sym, "technicals.sar.ep.one_year.ep", ep)
        update_field(collection, sym, "technicals.sar.ep.one_year.num_trades", len(sw))
        update_field(collection, sym, "technicals.sar.ep.one_year.price_change", change)
        update_field(collection, sym, "technicals.sar.ep.one_year.alpha", alpha)

        duration=relativedelta(months=6)
        sw = calc_psar(copy.deepcopy(df), duration)
        i = hdf5.get_nearest_index(df, (df.index[-1]-duration).to_pydatetime().date())
        change = percent_change(df.iloc[i]['Adj Close'], df['Adj Close'][-1])
        ep = np.nan
        alpha = np.nan
        if not sw['ep'].empty:
            ep = sw.ep[-1] - 1
            alpha = percent_change(change, ep)
        update_field(collection, sym, "technicals.sar.ep.six_months.ep", ep)
        update_field(collection, sym, "technicals.sar.ep.six_months.num_trades", len(sw))
        update_field(collection, sym, "technicals.sar.ep.six_months.price_change", change)
        update_field(collection, sym, "technicals.sar.ep.six_months.alpha", alpha)

        duration=relativedelta(months=3)
        sw = calc_psar(copy.deepcopy(df), duration)
        i = hdf5.get_nearest_index(df, (df.index[-1]-duration).to_pydatetime().date())
        change = percent_change(df.iloc[i]['Adj Close'], df['Adj Close'][-1])
        ep = np.nan
        alpha = np.nan
        if not sw['ep'].empty:
            ep = sw.ep[-1] - 1
            alpha = percent_change(change, ep)
        update_field(collection, sym, "technicals.sar.ep.three_months.ep", ep)
        update_field(collection, sym, "technicals.sar.ep.three_months.num_trades", len(sw))
        update_field(collection, sym, "technicals.sar.ep.three_months.price_change", change)
        update_field(collection, sym, "technicals.sar.ep.three_months.alpha", alpha)

        duration=relativedelta(months=1)
        sw = calc_psar(copy.deepcopy(df), duration)
        i = hdf5.get_nearest_index(df, (df.index[-1]-duration).to_pydatetime().date())
        change = percent_change(df.iloc[i]['Adj Close'], df['Adj Close'][-1])
        ep = np.nan
        alpha = np.nan
        if not sw['ep'].empty:
            ep = sw.ep[-1] - 1
            alpha = percent_change(change, ep)
        update_field(collection, sym, "technicals.sar.ep.one_month.ep", ep)
        update_field(collection, sym, "technicals.sar.ep.one_month.num_trades", len(sw))
        update_field(collection, sym, "technicals.sar.ep.one_month.price_change", change)
        update_field(collection, sym, "technicals.sar.ep.one_month.alpha", alpha)

        change = percent_change(sar[-1], df['Adj Close'][-1])
        update_field(collection, sym, "technicals.sar.change", change)
    
        idx = sar.loc[sar.index[-1]-timedelta(60):].tail(60).idxmin()
        if type(idx) is pd.Timestamp:
            update_field(collection, sym, "technicals.sar.60day_min", sar[idx])
            update_field(collection, sym, "technicals.sar.60day_min_price", df.loc[idx]['Adj Close'])
            update_field(collection, sym, "technicals.sar.60day_min_price_date", idx.to_pydatetime())
            #update_field(collection, sym, "technicals.sar.60day_min_price_date", str(idx).split(' ')[0])
        else:
            update_field(collection, sym, "technicals.sar.60day_min", nan)
            update_field(collection, sym, "technicals.sar.60day_min_price", nan)
            update_field(collection, sym, "technicals.sar.60day_min_price_date", nan)
            #update_field(collection, sym, "technicals.sar.60day_min_price_date", nan)
    
        idx = sar.loc[sar.index[-1]-timedelta(60):].tail(60).idxmax()
        if type(idx) is pd.Timestamp:
            update_field(collection, sym, "technicals.sar.60day_max", sar[idx])
            update_field(collection, sym, "technicals.sar.60day_max_price", df.loc[idx]['Adj Close'])
            update_field(collection, sym, "technicals.sar.60day_max_price_date", idx.to_pydatetime())
            #update_field(collection, sym, "technicals.sar.60day_max_price_date", str(idx).split(' ')[0])
        else:
            update_field(collection, sym, "technicals.sar.60day_max", nan)
            update_field(collection, sym, "technicals.sar.60day_max_price", nan)
            update_field(collection, sym, "technicals.sar.60day_max_price_date", nan)
            #update_field(collection, sym, "technicals.sar.60day_max_price_date", nan)
        update_field(collection, sym, "technicals.sar.date", dt.combine(dt.now(), dt.min.time()))

def update_RSI_params(collection, sym, df):
    rsi = ta.rsi(df['Adj Close'])
    if len(rsi.index) == 0:
        update_field(collection, sym, "technicals.rsi", {})
    else:
        update_field(collection, sym, "technicals.rsi.latest", rsi.iloc[-1])
        idx = rsi.loc[rsi.index[-1]-timedelta(60):].tail(60).idxmin()
        if type(idx) is pd.Timestamp:
            update_field(collection, sym, "technicals.rsi.60day_min", rsi[idx])
            update_field(collection, sym, "technicals.rsi.60day_min_price", df.loc[idx]['Adj Close'])
            update_field(collection, sym, "technicals.rsi.60day_min_price_date", idx.to_pydatetime())
            #update_field(collection, sym, "technicals.rsi.60day_min_price_date", str(idx).split(' ')[0])
        else:
            update_field(collection, sym, "technicals.rsi.60day_min", nan)
            update_field(collection, sym, "technicals.rsi.60day_min_price", nan)
            update_field(collection, sym, "technicals.rsi.60day_min_price_date", nan)
            #update_field(collection, sym, "technicals.rsi.60day_min_price_date", nan)
    
        idx = rsi.loc[rsi.index[-1]-timedelta(60):].tail(60).idxmax()
        if type(idx) is pd.Timestamp:
            update_field(collection, sym, "technicals.rsi.60day_max", rsi[idx])
            update_field(collection, sym, "technicals.rsi.60day_max_price", df.loc[idx]['Adj Close'])
            update_field(collection, sym, "technicals.rsi.60day_max_price_date", idx.to_pydatetime())
            #update_field(collection, sym, "technicals.rsi.60day_max_price_date", str(idx).split(' ')[0])
        else:
            update_field(collection, sym, "technicals.rsi.60day_max", nan)
            update_field(collection, sym, "technicals.rsi.60day_max_price", nan)
            update_field(collection, sym, "technicals.rsi.60day_max_price_date", nan)
            #update_field(collection, sym, "technicals.rsi.60day_max_price_date", nan)
        return rsi

def update_BB_params(collection, sym, df):
    #bbands = ta.bbands(df['Adj Close'])
    ub,mb,lb = talib.BBANDS(df['Adj Close'], timeperiod=20)
    if ub.empty:
        update_field(collection, sym, "technicals.bbands", {})
    else:
        update_field(collection, sym, "technicals.bbands.lower", lb[-1])
        update_field(collection, sym, "technicals.bbands.sma_20", mb[-1])
        update_field(collection, sym, "technicals.bbands.upper", ub[-1])
        # If the price is close to or above the upper band, its an uptrend and if close to lower band,
        # its a downtrend.
        update_field(collection, sym, "technicals.bbands.uptrend", df['Adj Close'][-1]/ub[-1])
        update_field(collection, sym, "technicals.bbands.downtrend", lb[-1]/df['Adj Close'][-1])

def update_AROON_params(collection, sym, df):
    # A high or low are tracked by AROON up and AROON down respectively.
    aroon_down, aroon_up = talib.AROON(df['High'], df['Low'], timeperiod=25)
    update_field(collection, sym, "technicals.aroon.down", aroon_down[-1])
    update_field(collection, sym, "technicals.aroon.up", aroon_up[-1])

def update_ATR_params(collection, sym, df, rsi=None):
    atr = ta.atr(df['High'], df['Low'], df['Adj Close'])
    if rsi is None:
        rsi = ta.rsi(df['Adj Close'])

    if len(atr.index) == 0:
        update_field(collection, sym, "technicals.atr", {})
    else:
        update_field(collection, sym, "technicals.atr.latest", atr.iloc[-1])
        idx = atr.loc[atr.index[-1]-timedelta(60):].tail(60).idxmin()
    
        if type(idx) is pd.Timestamp:
            update_field(collection, sym, "technicals.atr.60day_min", atr[idx])
            update_field(collection, sym, "technicals.atr.60day_min_price", df.loc[idx]['Adj Close'])
            update_field(collection, sym, "technicals.atr.60day_min_price_date", idx.to_pydatetime())
            #update_field(collection, sym, "technicals.atr.60day_min_price_date", str(idx).split(' ')[0])
        else:
            update_field(collection, sym, "technicals.atr.60day_min", "")
            update_field(collection, sym, "technicals.atr.60day_min_price", "")
            update_field(collection, sym, "technicals.atr.60day_min_price_date", "")
            #update_field(collection, sym, "technicals.atr.60day_min_price_date", "")
    
        idx = atr.loc[rsi.index[-1]-timedelta(60):].tail(60).idxmax()
        if type(idx) is pd.Timestamp:
            update_field(collection, sym, "technicals.atr.60day_max", atr[idx])
            update_field(collection, sym, "technicals.atr.60day_max_price", df.loc[idx]['Adj Close'])
            update_field(collection, sym, "technicals.atr.60day_max_price_date", idx.to_pydatetime())
            #update_field(collection, sym, "technicals.atr.60day_max_price_date", str(idx).split(' ')[0])
        else:
            update_field(collection, sym, "technicals.atr.60day_max", "")
            update_field(collection, sym, "technicals.atr.60day_max_price", "")
            update_field(collection, sym, "technicals.atr.60day_max_price_date", "")
            #update_field(collection, sym, "technicals.atr.60day_max_price_date", "")
            return atr

def update_chandelier_params(collection, sym, df, atr=None):
    if atr is None:
        atr = ta.atr(df['High'], df['Low'], df['Adj Close'])

    # Calculated using the ATR
    if len(atr.index) == 0:
        update_field(collection, sym, "technicals.chandelier.long", "-")
        update_field(collection, sym, "technicals.chandelier.short", "-")
        update_field(collection, sym, "technicals.chandelier.date", "-")
    else:
        rolling_low  = df["Low"][-22:].max()
        rolling_high = df['High'][-22:].max()
    
        # Chandelier Exit (long) = 22-day High - ATR(22) x 3
        # Chandelier Exit (short) = 22-day Low + ATR(22) x 3
    
        chandelier_long  = rolling_high - atr.iloc[-1] * 3
        chandelier_short = rolling_low  + atr.iloc[-1] * 3
        update_field(collection, sym, "technicals.chandelier.long", chandelier_long)
        update_field(collection, sym, "technicals.chandelier.short", chandelier_short)
        update_field(collection, sym, "technicals.chandelier.date", df.index[-1].to_pydatetime())

def update_ulcer_index_params(collection, sym, df):
    max_close = df['Adj Close'][-14:].max()
    df['Pct Drawdown'] = ((df['Adj Close'] - max_close)/max_close) * 100
    df['Pct Drawdown Sq'] = df['Pct Drawdown'].map(lambda x: x ** 2.0)
    
    square_avg = ((df['Pct Drawdown Sq'].sum())/float(len(df['Pct Drawdown Sq'])))
    ulcer_index = math.sqrt(square_avg)
    update_field(collection, sym, "technicals.ulcer_index", ulcer_index)

def update_money_flow_index_params(collection, sym, df):
    mf = ((df.iloc[-1]['Low'] + df.iloc[-1]['High'] + df.iloc[-1]['Adj Close'] ) / 3) * df.iloc[-1]['Volume']
    update_field(collection, sym, "technicals.mf", mf)
    update_candlesticks(collection, sym, df)

def update_price_trend(collection, sym, df, end, duration, duration_text):
    eindex = get_nearest_index(df, end)
    sindex = get_nearest_index(df, end-duration)
    cur_df = df.iloc[sindex:eindex]['Adj Close']

    if not cur_df.empty:
        # Calculate trend for that particular period
        coefficients, residuals, _, _, _ = np.polyfit(range(len(cur_df.index)), cur_df, 1, full=True)

        # Slope indicates the trend.
        # The slope is 
        # - positive if the price is going up.
        # - negative if the price is moving down.
        # - 0 if the price is constant.
        # The slope value closer to 0 indicates that the 
        # price didn't change much during that period.
        # The other values indicates the strength of the trend
        # in their respective directions.
        slope = coefficients[0]
        # Mean Square Error
        mse = residuals[0]/(len(cur_df.index))
        # Normalised Mean Square Error
        nrmse = np.sqrt(mse)/(cur_df.max() - cur_df.min())

        update_field(collection, sym, "technicals.price_trend."+duration_text+".slope", slope)
        update_field(collection, sym, "technicals.price_trend."+duration_text+".error", nrmse)

def update_price_trend_params(collection, sym, df):

    end = df.index[-1].date()
    # Ten Year trend
    update_price_trend(collection, sym, df, end, relativedelta(years=10), 'ten_year')
    # Five Year trend
    update_price_trend(collection, sym, df, end, relativedelta(years=5), 'five_year')
    # Two Year trend
    update_price_trend(collection, sym, df, end, relativedelta(years=2), 'two_year')
    # Yearly trend
    update_price_trend(collection, sym, df, end, relativedelta(years=1), 'year')
    # Half-Yearly trend
    update_price_trend(collection, sym, df, end, relativedelta(months=6), 'half_year')
    # Quarterly trend 
    update_price_trend(collection, sym, df, end, relativedelta(months=3), 'quarter')
    # Monthly trend
    update_price_trend(collection, sym, df, end, relativedelta(months=1), 'month')
    # Bi-Weekly trend
    update_price_trend(collection, sym, df, end, relativedelta(weeks=2), 'two_week')
    # Weekly trend
    update_price_trend(collection, sym, df, end, relativedelta(weeks=1), 'week')
    

def update_tech_analysis_params(sym, core, sem=None):

    aff = 0 | 1 << core
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    c  = open_db_client()
    db = c['Stocks']
    collection=db.US_Stocks
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

    try:
        query = 'select Date, Open, High, Low, Volume, `Adj Close` from {}'.format(get_symbol_table_name(sym))
        #query = 'select Date, `Adj Close` from {} where Date between \'{}\' and \'{}\''.format(get_symbol_table_name(sym), sdate.strftime("%Y-%m-%d"), edate.strftime("%Y-%m-%d"))
        df = read_from_sql(query, mysql_engine)
 
        if df.empty or len(df.index) == 1:
            print("Empty df")
            update_field(collection, sym, "technicals.rsi", {})
            update_field(collection, sym, "technicals.bbands", {})
            update_field(collection, sym, "technicals.candlesticks", {})
            update_field(collection, sym, "technicals.aroon", {})
            update_field(collection, sym, "technicals.sar", {})
            update_field(collection, sym, "technicals.atr", {})
            update_field(collection, sym, "technicals.chandelier", {})
            update_field(collection, sym, "technicals.mf", nan)
            update_field(collection, sym, "technicals.ulcer_index", nan)
            update_field(collection, sym, "technicals.price_trend", {})
        else:
            # bollinger bands
            update_BB_params(collection, sym, df)

            # AROON Indicator. Its a trend indicator.
            # A high or low are tracked by AROON up and AROON down respectively.
            update_AROON_params(collection, sym, df)

            # SAR Calculation
            update_SAR_params(collection, sym, df)

            # RSI Calculation
            rsi = update_RSI_params(collection, sym, df)

            # ATR. Average True Range. Its a volatility Indicator.
            # High and low values represents respective volatility.
            atr = update_ATR_params(collection, sym, df, rsi)

            # Chandelier Exit. Its a volatility based system that is designed to ensure traders do not exit a long position
            # too early in an uptrend or too late in a downtrend.
            # http://kaushik316-blog.logdown.com/posts/1964522
            # https://school.stockcharts.com/doku.php?id=technical_indicators:chandelier_exit
            update_chandelier_params(collection, sym, df, atr)

            # Ulcer Index. ITs a volatility tracker designed to measure downside risk.
            # Based on the closing prices, the Ulcer Index measures volatility based on price depreciation from its high over
            # a specific look-back period. The index is zero if the prcies close higher each period. In such a situation, the
            # downside risk is zero since the price steadily increases without ever falling.
            update_ulcer_index_params(collection, sym, df)

            # Money Flow index
            update_money_flow_index_params(collection, sym, df)

            # Calculate trend
            update_price_trend_params(collection, sym, df)

        update_field(collection, sym, "technicals.date", dt.combine(dt.now(), dt.min.time()))
    finally:
        close_db_client(c)
        close_sql_connection(mysql_engine)
        if sem:
            sem.release()

def update_all_tech_analysis_params(country='US'):
    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    num_processes = num_cores * 2
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes

    sort = [-1, 1][dt.now().day % 2 == 0]
    stocks=db.US_Stocks.find({"$and":[{'General.Exchange':{"$in":major_exchanges}},\
                                        {'General.Type':'Common Stock'}, \
                                        {'General.IsDelisted': False}, \
                                        {'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}}, \
                                        #{'$or':[\
                                        #        {'technicals.date': {"$exists": False}},\
                                        #        {'technicals.date':{'$lt': get_latest_trading_day()}}
                                        #        ]\
                                        #},\
                                        {'dates.mysql_price_pull_success':True}, \
                                    ]}).batch_size(10).sort([["General.Code",sort]]).allow_disk_use(True)
                                    #]}).batch_size(10).sort([["sno",1]]).allow_disk_use(True)

    #stocks=db.US_Stocks.find({'General.Code':'AFCG'})
    print("Tech analysis, total stocks:", stocks.count())
    i=0
    try:
        for i, stk in enumerate(stocks):
            print("Tech analysis params: %d: Symbol: %r" %(i, stk['bscs']['symbol']))
            sem.acquire()
            #update_tech_analysis_params(stk['bscs']['symbol'], 0)
            processes[i%num_processes] = multiprocessing.Process(target=update_tech_analysis_params, args=(stk['bscs']['symbol'], i%num_cores, sem,))
            processes[i%num_processes].start()
    finally:
        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()

    print("Tech params: Stocks tried :%r"%(i))

    close_db_client(c)
    close_sql_connection(mysql_engine)

def price_range_anomoly(country, mysql_engine, sym, df):
    if len(df.index) < 1:
        return

    start = dt.strptime("1970-01-01", "%Y-%m-%d").date()
    end = dt.now().date()
    try:
        ddf = pdr.DataReader(sym,'yahoo',start, end)
        ddf = ddf[~ddf.index.isin(df.index)]
        if not ddf.empty:
            print(ddf)
            mysql_update_table(mysql_engine, get_symbol_table_name(sym), ddf, insert=True)
    except Exception as E:
        print(str(E))
        pass

    #start = df.index[0]
    #for i in df.index[1:]:
    #    end = i
    #    if (end-start) > timedelta(7):
    #        print("symbol:%r, start:%r, end: %r" %(sym, start, end))
    #        try:
    #            ddf = pdr.DataReader(sym,'yahoo',start.to_pydatetime()+timedelta(1),
    #                                end.to_pydatetime()-timedelta(1), retry_count=3)
    #            mysql_update_table(mysql_engine, get_symbol_table_name(sym), ddf, insert=True)
    #        except Exception as E:
    #            print("Symbol: %r, exception: %r" %(sym, str(E)))
    #            pass

    #    start = end

# Some times, due to errors from yahoo finance, the application misses some
# of the price entries related to a particular date. This could cause the loss
# in the sequence of the series. Check those issues are try to get the price changes
# again. The logic is to check if there is atleast 4 days of difference between
# consecutive price changes(assuming a long holiday). If so, truncate from that point
# in the mysql database and get the prices again.
def check_price_range_anomolies(country='US'):
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    symbols = get_symbols_from_sql(country, mysql_engine)

    for i, sym in enumerate(symbols):
        if sym == '':
            continue
        print("%d: Symbol: %r" %(i, sym))
        if i % 200  == 0:
            change_vpn()
        query = 'select Date, `Adj Close` from {}'.format(get_symbol_table_name(sym))
        df = read_from_sql(query, mysql_engine)
        price_range_anomoly(country, mysql_engine, sym, df)

    close_sql_connection(mysql_engine)


def update_all_price_volume_db(country):
    global j
    max_threads = 10
    #max_threads = thread_factor
    hdf5_sem = threading.BoundedSemaphore(max_threads)
    db_sem = threading.BoundedSemaphore(max_threads)
    #vpn_event = threading.Event()
    #vpn_event.set()
    vpn_event=None
    db_lock = threading.Lock()
    today=str(dt.now().date())
    count=0
    i=0

    if country != 'US' and country != 'India':
        PRINT_ERR("Unknown Country")
        return

    change_vpn()
    fork_hdf5_process(country, hdf5_sem, vpn_event)
    #fork_db_process(country, db_sem, db_lock, vpn_event)
    #hdf5_process = multiprocessing.Process(target=fork_hdf5_process, args=(country, hdf5_sem,vpn_event))
    #db_process = multiprocessing.Process(target=fork_db_process, args=(country, db_sem, db_lock, vpn_event))
    #try:
    #    hdf5_process.start()
    #    db_process.start()
    #finally:
    #    db_process.join()
    #    hdf5_process.join()
    #print("Exiting hdf5 and db processes")

#Find missing entries in the db.
# Compare with entries in BSE_Stocks.xls
def find_files():
    c  = open_db_client()
    db = c['Stocks']
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
    close_db_client(c)

def get_last_weekday(d):
    res = len(pd.bdate_range(d,d))
    # If Weekend
    if res == 0:
        # d.weekday() returns (0-6).
        # Values 5,6 corresponds to Saturday and Sunday.
        # Substract 4 to get the number of extra days
        # after a weekday.
        # Remove those many number of days from the current date.
        # It should give the last weekday.
        d = d-timedelta(d.weekday()-4)
    return d

def get_latest_trading_day():
    return trading_day()

def get_previous_trading_day():
    day = trading_day() - timedelta(1)
    return trading_day(day)

def trading_day(lt_date=None):
    if lt_date is None:
        lt_date = dt.combine(dt.now().date(), dt.min.time())

    lt_date = get_last_weekday(lt_date)

    table_name = 'US_Holiday_List'
    mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Data')
    if not mysql_exists_table(mysql_engine, table_name):
        update_US_holiday_list()
    query = 'select Date from {}'.format(table_name)
    ddf = read_from_sql(query, mysql_engine)
    close_sql_connection(mysql_engine)
 
    while True:
        # If today is a holiday,
        if lt_date in ddf.index:
            # Get the previous day
            lt_date = lt_date - timedelta(1)
            # Check and get the last week day
            lt_date = get_last_weekday(lt_date)
        else:
            break

    return lt_date

def get_iex_symbols():
    c  = open_db_client()
    db = c['Stocks']
    j = db.US_Stocks_List.find({}).count()

    df = data.get_iex_symbols()
    df = df[df['name']!='']
    df = df[df['type']!='crypto']
    # Exclude all symbols ending with +,=,-
    # TODO: Remove all symbols ending with special characters
    df = df[df['symbol'].str.match(r'(.*[\=|\+|\-]$)')==False]
    entries = []

    for index, d in df.iterrows():
        obj = db.US_Stocks_List.find({"symbol":d['symbol']})
        if obj.count() == 0:
            print("%r: %r" %(d['symbol'],d['name']))
            entry = []
            entry.append(d['symbol'])
            entry.append(d['name'])
            entries.append(entry)
            j+=1
            stk = {"symbol" : d['symbol'], "Name" : d['name'], "data" : "NO", "parsed" : "NO", "sno": j}
            db.US_Stocks_List.insert_one(stk)

    close_db_client(c)
    return entries

def get_eod_all_trading_symbols(exchanges=all_exchanges, quoteType='Common Stock'):
    url = 'https://eodhistoricaldata.com/api/exchange-symbol-list/US?api_token='+get_eod_token_id()
    ret = requests.get(url)
    df  = pd.read_csv(StringIO(ret.text), skipfooter=1, parse_dates=[0], index_col=0, engine='python')
    df['Symbol'] = df.index

    # Drop Null
    #df = df.dropna()

    # Filter based on quoteType
    df = df[df['Type']==quoteType]

    # Filter based on exchange
    df = df[df['Exchange'].isin(exchanges)]

    return df

def add_symbol_to_database(d, db=None, mysql_engine=None):
    local_db    = False
    local_mysql = False

    if db is None:
        c  = open_db_client()
        db = c['Stocks']
        local_db = True

    if mysql_engine is None:
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Data')
        local_mysql = True

    sno = db.US_Stocks.find({}).count()
    bscs = {"symbol" : d['Symbol'], "name" : d['Name'], "exchange": d['Exchange'], "quoteType": d['Type']}
    stk  = {"bscs" : bscs, "sno": sno}
    print("Adding new symbol: %s: %s" %(d['Symbol'], d['Name']))
    db.US_Stocks.insert_one(stk)
    
    if d['Exchange'] not in major_exchanges:
        general_only=True
    else:
        general_only=False

    update_technicals(stk, general_only=general_only)
    
    stk_df = pd.DataFrame([list(d.values)], columns=list(d.index), index=[d['Symbol']])

    table_name = 'US_All_Stocks_List'
    mysql_check_n_create_table(mysql_engine, table_name, empty_table=True)
    mysql_update_table(mysql_engine, table_name, stk_df, check=True, insert=True, unknown_table=False, cols_type='text', temp=True, date_column=False, format_columns=False, primary_key=True, empty_table=True)

    if local_db:
        close_db_client(c)
    if local_mysql:
        close_sql_connection(mysql_engine)

def get_eod_symbols():
    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Data')

    df = get_eod_all_trading_symbols()

    #table_name = 'US_All_Stocks_List'
    #mysql_check_n_create_table(mysql_engine, table_name, empty_table=True)
    #query = 'select * from {}'.format(table_name)
    #ddf = read_from_sql(query, mysql_engine, date=False)
    #if ddf.empty:
    #    mysql_update_table(mysql_engine, table_name, df, check=True, insert=True, unknown_table=False, cols_type='text', temp=True, date_column=False, format_columns=False, primary_key=True, empty_table=True)
        
    # Exclude all symbols ending with +,=,-
    # TODO: Remove all symbols ending with special characters
    #df = df[df['symbol'].str.match(r'(.*[\=|\+|\-]$)')==False]
    entries = []

    for index, d in df.iterrows():
        obj = db.US_Stocks.find({"bscs.symbol":d['Symbol']})
        if obj.count() == 0:
            print("%r: %r: %r: %r" %(d['Symbol'],d['Name'], d['Exchange'], d['Type']))
            add_symbol_to_database(d, db, mysql_engine)

            #bscs = {"symbol" : d['Symbol'], "name" : d['Name'], "exchange": d['Exchange'], "quoteType": d['Type']}
            #stk  = {"bscs" : bscs, "sno": j}
            #db.US_Stocks.insert_one(stk)

            #url='https://eodhistoricaldata.com/api/fundamentals/'+d['Symbol']+'?api_token='+get_eod_token_id()+'&filter=General'
            #ret = requests.get(url)
            #if ret.status_code == 200:
            #    general = ret.json()
            #    if len(general) != 0 or isinstance(general, dict):
            #        if general != 'NA':
            #           db.US_Stocks.update({'bscs.symbol': d['Symbol']}, {'$set': {'General': general}})

            #stk_df = df[df['Symbol'] == d['Symbol']]
            #mysql_update_table(mysql_engine, table_name, stk_df, check=True, insert=True, unknown_table=False, cols_type='text', temp=True, date_column=False, format_columns=False, primary_key=True, empty_table=True)
            entry = []
            entry.append(d['Symbol'])
            entry.append(d['Name'])
            entry.append(d['Exchange'])
            entries.append(entry)
        else:
            db.US_Stocks.update({'bscs.symbol': d['Symbol']}, {'$set': {"bscs.exchange": d['Exchange']}})
            db.US_Stocks.update({'bscs.symbol': d['Symbol']}, {'$set': {"bscs.quoteType": d['Type']}})
            db.US_Stocks.update({'bscs.symbol': d['Symbol']}, {'$set': {"bscs.name": d['Name']}})
    set_sno('US')

    close_db_client(c)
    close_sql_connection(mysql_engine)
    return entries
 
def build_US_Stocks_List(excel_file):
    c  = open_db_client()
    db = c['Stocks']
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

    close_db_client(c)
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
    c  = open_db_client()
    db = c['Stocks']
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
    close_db_client()

def build_US_all_EPS():
    print("****************** Building US EPS ******************")
    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')

    #docs = db.US_Stocks.find({"$and": [{"bscs.since":{"$exists": False}}, {"ignore":"No"}]},no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.US_Stocks.find({"bscs.since":{"$exists": False}},no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.US_Stocks.find({"bscs.symbol":"BKD"}).sort([["sno",1]])
    #docs = db.US_Stocks.find({}).sort([["sno",1]])
    #docs  = db.US_Stocks.find(get_nin("file.txt", "nins.txt"))
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"fig.DIVIDEND_History": {"$exists": False}},{"fig.Split_History": {"$exists": False}}, {"bscs.symbol":{"$ne": "ARR"}}]})
    #docs = db.US_Stocks.find({"fig.EPS_History": {"$exists": False}})
    #stocks = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, ]},no_cursor_timeout=True)
    #docs = db.US_Stocks.find({"$and": [{"fig.EPS_History": {"$exists": False}}, {"bscs.symbol":{"$nin": ["DAIO", "IBCP", "MRTN", "SLGN"]}}]},no_cursor_timeout=True)
    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    count = stocks.count()
    print(count)
    if count == 0:
        print("***************** Completed fetching EPS  *************")
        return
    start = dt.now()
    for stock in stocks:
        try:
            sno = stock['sno']
            if sno > 0:
                print("%d: %s: %s"%(sno,stock['bscs']['symbol'],stock['bscs']['name']))
                #write_stock_to_file(stock['bscs']['symbol'], "file2.txt", "a")
                internet.populate_US_EPS(stock)
            if (dt.now()-start).seconds > 1800:
                start = dt.now()
                change_vpn()

        except Exception as E:
            print(str(E))
            continue

    close_db_client(c)

""" Updated EPS for all existing stocks in the database"""
def update_US_all_EPS():
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')
    c  = open_db_client()
    db = c['Stocks']
    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    count = stocks.count()
    print(count)
    if count == 0:
        return
    for i, stock in enumerate(stocks):
        #if i % 10 == 0:
        #    change_vpn()
        try:
            print("%d: %s: %s"%(i,stock['bscs']['symbol'],stock['bscs']['name']))
            internet.populate_US_EPS(stock, mysql_engine, db)
        except Exception as E:
            print(str(E))
            continue
        
    close_db_client(c)
    close_sql_connection(mysql_engine)

def build_US_all_earnings_estimates():

    c  = open_db_client()
    db = c['Stocks']
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
    
    close_db_client(c)

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
    br  = internet.open_browser()
    br.get(nasdaq_url)
    internet.close_browser(br)


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

def US_update_split_history():
    #First get total number of web pages with symbol changes
    url = 'https://www.nasdaq.com/market-activity/stocks/symbol-change-history'
    #br  = internet.open_browser()
    br  = internet.open_browser('headless')
    br.get(url)
    br.maximize_window()

    df = pd.DataFrame()
    df = pd.read_html(br.page_source)
    if len(df) == 0:
        return
    df = df[0]

    br.execute_script("window.scrollTo(0, 2000)")

    #we = br.find_element_by_css_selector("button.pagination__page:nth-child(2)")
    we = br.find_element_by_class_name("pagination__next")
    a = internet.get_action_chain(br)
    h = a.move_to_element(we)
    h.click().perform()
    rdf = pd.read_html(br.page_source)
    df  = df.append(rdf[0])

    del df['Company Name']
    internet.close_browser(br)

    #br  = internet.open_browser('headless')
    #url = 'https://old.nasdaq.com/markets/stocks/symbol-change-history.aspx?sortby=EFFECTIVE&descending=Y'
    #br.get(url)
    #page = br.page_source
    #soup = parse_html.get_soup(page)
    #last_page = soup.find(id='two_column_main_content_lb_LastPage')
    #last_page = last_page.attrs.get('href')
    #pages = re.split(r'page=', last_page)
    #if len(pages) > 1:
    #    last_page = pages[-1]
    #else:
    #    last_page = 1
    ##internet.close_browser(br)

    ## Retrieve and form a dataframe of all symbol changes.
    #df = pd.DataFrame()
    #for i in range(1, int(last_page)+1):
    #    url = 'https://old.nasdaq.com/markets/stocks/symbol-change-history.aspx?sortby=EFFECTIVE&descending=Y&page=%s' %(i)
    #    #url = 'https://www.nasdaq.com/market-activity/stocks/symbol-change-history.aspx?sortby=EFFECTIVE&descending=Y&page=%s' %(i)
    #    br.get(url)
    #    rdf = pd.read_html(br.page_source)
    #    df  = df.append(rdf[0])

    cols = list(df.columns)
    new_cols = {}
    for c in cols:
        new_cols[c] = c.replace(' ', '_')
    df.rename(columns=new_cols, inplace=True)
    df.index=pd.RangeIndex(len(df.index))
    #The below two statements are required to convert date from YY/mm/dd to YY-mm-dd
    df['Effective_Date'] = pd.to_datetime(df['Effective_Date'])
    df['Effective_Date'] = df['Effective_Date'].astype('str')

    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Changes')
    price_change_mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    if mysql_exists_table(mysql_engine, 'Symbol_Changes'):
        query = 'select Old_Symbol, New_Symbol, Effective_Date from {} order by Effective_Date desc'.format('Symbol_Changes')
        ddf = read_from_sql(query, mysql_engine, date=False)
        if not ddf.empty:
            ddf['Effective_Date'] = ddf['Effective_Date'].astype('str')
            df = df_difference(df, ddf)
            #df = df[~df.isin(ddf)].dropna()
            #df = df[~df.index.isin(ddf.index)]

    # Convert to string. Just for info.
    #df['Effective_Date']=df['Effective_Date'].astype('str')
    if not df.empty:
        # Convert to datetime
        df['Effective_Date'] = pd.to_datetime(df['Effective_Date'])
        mysql_update_table(mysql_engine, 'Symbol_Changes', df, check=True, insert=True, unknown_table=True, cols_type='fin', temp=True, date_column=False)

        print("Sending email of the list of new symbol changes")
        subject='Symbol Changes: %r' %(str(datetime.datetime.now().date()))
        internet.send_email2('petlafin@gmail.com', 'Tasche3#Gm', 'petlafin@gmail.com', subject, df.to_html())
        
    # Read all symbol's information that are not yet updated to mongodb and price changes.
    query = 'select * from Symbol_Changes  where updated_to_mongodb = \'NO\' and tried_count < 5 order by Effective_Date desc'
    df = read_from_sql(query, mysql_engine, date=False)
    c  = open_db_client()
    db = c['Stocks']
    for index, d in df.iterrows():
        old_symbol = d['Old_Symbol']
        new_symbol = d['New_Symbol']
        
        stks = db.US_Stocks.find({'bscs.symbol':old_symbol})
        # old symbol not in our database
        if stks.count() == 0:
            if db.US_Stocks.find({"bscs.symbol":new_symbol}).count() > 0:
                print("%r: %r: %r" %(index, old_symbol, new_symbol))
                # New symbol already exists in mongodb
                # Update Symbol_changes table 'updated_to_mongodb field and updated date field
                query = 'update Symbol_Changes set updated_to_mongodb=\'YES\' where Old_Symbol=\'{}\''.format(old_symbol)
                mysql_engine.execute(query)
                query = 'update Symbol_Changes set updated_date=\'{}\' where Old_Symbol=\'{}\''.format(str(dt.now().date()), old_symbol)
                mysql_engine.execute(query)
        # old symbol in our database
        else:
            print("%r: %r: %r" %(index, old_symbol, new_symbol))
            stk = stks[0]
            query = 'select tried_count from Symbol_Changes where Old_Symbol=\'{}\''.format(old_symbol)
            tried_count = read_from_sql(query, mysql_engine, date=False)
            tried_count = tried_count.iloc[0]['tried_count'] + 1
            query = 'update Symbol_Changes set tried_count={} where Old_Symbol=\'{}\''.format(tried_count, old_symbol)
            mysql_engine.execute(query)

            #if not price_change_mysql_engine.has_table('STK'+old_symbol.replace('.','_')):
            #    print("Symbol %s does not have a table in mysql database" %(old_symbol))
            #    continue

            # Check if the new_symbol already exists in your databases.
            # If so, break there and manually handle the case.
            if db.US_Stocks.find({'bscs.symbol':new_symbol}).count() > 0 or price_change_mysql_engine.has_table('STK'+new_symbol.replace('.','_')):
                print("new_sym: %r, old_sym: %r, new_symbol entry already exists in mongodb or mysqldb" %(new_symbol, old_symbol))
                #print("Skipping")
                #continue
                #print("Handle manually")
                #choice = input("1. Delete the new symbol info \n2. Delete the old symbol info\nChoice : ")
                sym = new_symbol

                # If there exists an old table, drop the new table and
                # update the name of the old table with the new table.
                if price_change_mysql_engine.has_table('STK'+old_symbol.replace('.','_')):
                    query = 'drop table {}'.format('STK'+sym.replace('.','_'))
                    #query = 'drop table {}'.format('STK'+new_symbol.replace('.','_'))
                    price_change_mysql_engine.execute(query)
                    #query = 'alter table {} rename to {};'.format('STK'+old_symbol.replace('.','_'), 'STK'+new_symbol.replace('.','_'))
                    #price_change_mysql_engine.execute(query)

                # Delete all new symbol financial data entries
                query = 'delete from US_Stocks_Fin.income_quart_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.cash_quart_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.balance_quart_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.income_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.cash_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.balance_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
 
                # Remove new symbol information from the mongodb
                db.US_Stocks.remove({"bscs.symbol" : sym},1)
                db.US_Stocks_List.remove({"symbol" : sym},1)
                #if choice == '2':
                #    continue

            # Update the symbol to new symbol
            db.US_Stocks.update({'bscs.symbol': old_symbol}, {'$set': {"bscs.symbol": new_symbol}})
            # Update the old symbol in US_Stocks_List with the new symbol
            db.US_Stocks_List.update({'symbol': old_symbol}, {'$set': {'symbol': new_symbol}})
            # Save previous symbols information
            prev_syms = []
            prev_names = []
            prev_syms_till_date = []
            if 'previous_symbols' in stk['bscs'].keys():
                prev_syms = stk['bscs']['previous_symbols']['Names']
                if 'Company_Names' in stk['bscs']['previous_symbols'].keys():
                    prev_names = stk['bscs']['previous_symbols']['Company_Names']
                prev_syms_till_date = stk['bscs']['previous_symbols']['Till_Date']
           
            prev_syms.append(old_symbol)
            prev_names.append(stk['bscs']['name'])
            prev_syms_till_date.append(str(d['Effective_Date'] - timedelta(1)))
            db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.previous_symbols.Names": prev_syms}})
            db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.previous_symbols.Company_Names": prev_names}})
            db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.previous_symbols.Till_Date": prev_syms_till_date}})
            
            # Reset failcount
            if 'mysql_price_failcount' in stk['bscs'].keys():
                db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"failcount.mysql_price_failcount": 0}})
                db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.trading": "YES"}})
           
            # Rename table with the new symbol name
            if price_change_mysql_engine.has_table('STK'+old_symbol.replace('.','_')):
                query = 'alter table {} rename to {};'.format('STK'+old_symbol.replace('.','_'), 'STK'+new_symbol.replace('.','_'))
                price_change_mysql_engine.execute(query)

            # Update Symbol_changes table 'updated_to_mongodb field and updated date field
            query = 'update Symbol_Changes set updated_to_mongodb=\'YES\' where Old_Symbol=\'{}\''.format(old_symbol)
            mysql_engine.execute(query)
            query = 'update Symbol_Changes set updated_date=\'{}\' where Old_Symbol=\'{}\''.format(str(dt.now().date()), old_symbol)
            mysql_engine.execute(query)

    close_sql_connection(mysql_engine)
    close_sql_connection(price_change_mysql_engine)
    close_db_client(c)


def update_symbol_name_changes():
    #First get total number of web pages with symbol changes
    url = 'https://www.nasdaq.com/market-activity/stocks/symbol-change-history'
    #br  = internet.open_browser()
    br  = internet.open_browser('headless')
    br.get(url)
    br.maximize_window()

    df = pd.DataFrame()
    df = pd.read_html(br.page_source)
    if len(df) == 0:
        return
    df = df[0]

    br.execute_script("window.scrollTo(0, 2000)")

    #we = br.find_element_by_css_selector("button.pagination__page:nth-child(2)")
    we = br.find_element_by_class_name("pagination__next")
    a = internet.get_action_chain(br)
    h = a.move_to_element(we)
    h.click().perform()
    rdf = pd.read_html(br.page_source)
    df  = df.append(rdf[0])

    del df['Company Name']
    internet.close_browser(br)

    #br  = internet.open_browser('headless')
    #url = 'https://old.nasdaq.com/markets/stocks/symbol-change-history.aspx?sortby=EFFECTIVE&descending=Y'
    #br.get(url)
    #page = br.page_source
    #soup = parse_html.get_soup(page)
    #last_page = soup.find(id='two_column_main_content_lb_LastPage')
    #last_page = last_page.attrs.get('href')
    #pages = re.split(r'page=', last_page)
    #if len(pages) > 1:
    #    last_page = pages[-1]
    #else:
    #    last_page = 1
    ##internet.close_browser(br)

    ## Retrieve and form a dataframe of all symbol changes.
    #df = pd.DataFrame()
    #for i in range(1, int(last_page)+1):
    #    url = 'https://old.nasdaq.com/markets/stocks/symbol-change-history.aspx?sortby=EFFECTIVE&descending=Y&page=%s' %(i)
    #    #url = 'https://www.nasdaq.com/market-activity/stocks/symbol-change-history.aspx?sortby=EFFECTIVE&descending=Y&page=%s' %(i)
    #    br.get(url)
    #    rdf = pd.read_html(br.page_source)
    #    df  = df.append(rdf[0])

    cols = list(df.columns)
    new_cols = {}
    for c in cols:
        new_cols[c] = c.replace(' ', '_')
    df.rename(columns=new_cols, inplace=True)
    df.index=pd.RangeIndex(len(df.index))
    #The below two statements are required to convert date from YY/mm/dd to YY-mm-dd
    df['Effective_Date'] = pd.to_datetime(df['Effective_Date'])
    df['Effective_Date'] = df['Effective_Date'].astype('str')

    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Changes')
    price_change_mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    if mysql_exists_table(mysql_engine, 'Symbol_Changes'):
        query = 'select Old_Symbol, New_Symbol, Effective_Date from {} order by Effective_Date desc'.format('Symbol_Changes')
        ddf = read_from_sql(query, mysql_engine, date=False)
        if not ddf.empty:
            ddf['Effective_Date'] = ddf['Effective_Date'].astype('str')
            df = df_difference(df, ddf)
            #df = df[~df.isin(ddf)].dropna()
            #df = df[~df.index.isin(ddf.index)]

    # Convert to string. Just for info.
    #df['Effective_Date']=df['Effective_Date'].astype('str')
    if not df.empty:
        # Convert to datetime
        df['Effective_Date'] = pd.to_datetime(df['Effective_Date'])
        mysql_update_table(mysql_engine, 'Symbol_Changes', df, check=True, insert=True, unknown_table=True, cols_type='fin', temp=True, date_column=False)

        print("Sending email of the list of new symbol changes")
        subject='Symbol Changes: %r' %(str(datetime.datetime.now().date()))
        internet.send_email2('petlafin@gmail.com', 'Tasche3#Gm', 'petlafin@gmail.com', subject, df.to_html())
        
    # Read all symbol's information that are not yet updated to mongodb and price changes.
    query = 'select * from Symbol_Changes  where updated_to_mongodb = \'NO\' and tried_count < 5 order by Effective_Date desc'
    df = read_from_sql(query, mysql_engine, date=False)
    c  = open_db_client()
    db = c['Stocks']
    for index, d in df.iterrows():
        old_symbol = d['Old_Symbol']
        new_symbol = d['New_Symbol']
        
        stks = db.US_Stocks.find({'bscs.symbol':old_symbol})
        # old symbol not in our database
        if stks.count() == 0:
            if db.US_Stocks.find({"bscs.symbol":new_symbol}).count() > 0:
                print("%r: %r: %r" %(index, old_symbol, new_symbol))
                # New symbol already exists in mongodb
                # Update Symbol_changes table 'updated_to_mongodb field and updated date field
                query = 'update Symbol_Changes set updated_to_mongodb=\'YES\' where Old_Symbol=\'{}\''.format(old_symbol)
                mysql_engine.execute(query)
                query = 'update Symbol_Changes set updated_date=\'{}\' where Old_Symbol=\'{}\''.format(str(dt.now().date()), old_symbol)
                mysql_engine.execute(query)
        # old symbol in our database
        else:
            print("%r: %r: %r" %(index, old_symbol, new_symbol))
            stk = stks[0]
            query = 'select tried_count from Symbol_Changes where Old_Symbol=\'{}\''.format(old_symbol)
            tried_count = read_from_sql(query, mysql_engine, date=False)
            tried_count = tried_count.iloc[0]['tried_count'] + 1
            query = 'update Symbol_Changes set tried_count={} where Old_Symbol=\'{}\''.format(tried_count, old_symbol)
            mysql_engine.execute(query)

            #if not price_change_mysql_engine.has_table('STK'+old_symbol.replace('.','_')):
            #    print("Symbol %s does not have a table in mysql database" %(old_symbol))
            #    continue

            # Check if the new_symbol already exists in your databases.
            # If so, break there and manually handle the case.
            if db.US_Stocks.find({'bscs.symbol':new_symbol}).count() > 0 or price_change_mysql_engine.has_table('STK'+new_symbol.replace('.','_')):
                print("new_sym: %r, old_sym: %r, new_symbol entry already exists in mongodb or mysqldb" %(new_symbol, old_symbol))
                #print("Skipping")
                #continue
                #print("Handle manually")
                #choice = input("1. Delete the new symbol info \n2. Delete the old symbol info\nChoice : ")
                sym = new_symbol

                # If there exists an old table, drop the new table and
                # update the name of the old table with the new table.
                if price_change_mysql_engine.has_table('STK'+old_symbol.replace('.','_')):
                    if price_change_mysql_engine.has_table('STK'+sym.replace('.','_')):
                        query = 'drop table {}'.format('STK'+sym.replace('.','_'))
                        #query = 'drop table {}'.format('STK'+new_symbol.replace('.','_'))
                        price_change_mysql_engine.execute(query)
                        #query = 'alter table {} rename to {};'.format('STK'+old_symbol.replace('.','_'), 'STK'+new_symbol.replace('.','_'))
                        #price_change_mysql_engine.execute(query)

                # Delete all new symbol financial data entries
                query = 'delete from US_Stocks_Fin.income_quart_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.cash_quart_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.balance_quart_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.income_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.cash_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
                query = 'delete from US_Stocks_Fin.balance_table where Symbol=\'{}\''.format(sym.replace('.','_'))
                price_change_mysql_engine.execute(query)
 
                # Remove new symbol information from the mongodb
                db.US_Stocks.remove({"bscs.symbol" : sym},1)
                db.US_Stocks_List.remove({"symbol" : sym},1)
                #if choice == '2':
                #    continue

            # Update the symbol to new symbol
            db.US_Stocks.update({'bscs.symbol': old_symbol}, {'$set': {"bscs.symbol": new_symbol}})
            # Update the old symbol in US_Stocks_List with the new symbol
            db.US_Stocks_List.update({'symbol': old_symbol}, {'$set': {'symbol': new_symbol}})
            # Save previous symbols information
            prev_syms = []
            prev_names = []
            prev_syms_till_date = []
            if 'previous_symbols' in stk['bscs'].keys():
                prev_syms = stk['bscs']['previous_symbols']['Names']
                if 'Company_Names' in stk['bscs']['previous_symbols'].keys():
                    prev_names = stk['bscs']['previous_symbols']['Company_Names']
                prev_syms_till_date = stk['bscs']['previous_symbols']['Till_Date']
           
            prev_syms.append(old_symbol)
            prev_names.append(stk['bscs']['name'])
            prev_syms_till_date.append(str(d['Effective_Date'] - timedelta(1)))
            db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.previous_symbols.Names": prev_syms}})
            db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.previous_symbols.Company_Names": prev_names}})
            db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.previous_symbols.Till_Date": prev_syms_till_date}})
            
            # Reset failcount
            if 'mysql_price_failcount' in stk['bscs'].keys():
                db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"failcount.mysql_price_failcount": 0}})
                db.US_Stocks.update({'bscs.symbol': new_symbol}, {'$set': {"bscs.trading": "YES"}})
           
            # Rename table with the new symbol name
            if price_change_mysql_engine.has_table('STK'+old_symbol.replace('.','_')):
                query = 'alter table {} rename to {};'.format('STK'+old_symbol.replace('.','_'), 'STK'+new_symbol.replace('.','_'))
                price_change_mysql_engine.execute(query)

            # Update Symbol_changes table 'updated_to_mongodb field and updated date field
            query = 'update Symbol_Changes set updated_to_mongodb=\'YES\' where Old_Symbol=\'{}\''.format(old_symbol)
            mysql_engine.execute(query)
            query = 'update Symbol_Changes set updated_date=\'{}\' where Old_Symbol=\'{}\''.format(str(dt.now().date()), old_symbol)
            mysql_engine.execute(query)

    close_sql_connection(mysql_engine)
    close_sql_connection(price_change_mysql_engine)
    close_db_client(c)

def build_US_All_Stocks_List():
    #get_US_Stock_list()
    new_stocks = [] 
    head=["Symbol", "Name", "Exchange"]
    #head=["Symbol", "Name", "Sector", "Industry", "Market Cap", "$Price"]#, "Max Price Change"]
    new_stocks.append(head)
    #new_stocks.extend(build_US_Stocks_List(conf.amex_stocks))
    #new_stocks.extend(build_US_Stocks_List(conf.nyse_stocks))
    #new_stocks.extend(build_US_Stocks_List(conf.nasdaq_stocks))
    #new_stocks.extend(get_iex_symbols())
    new_stocks.extend(get_eod_symbols())
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
    trials = 0
    while True:
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
            if (now - last_date) < timedelta(30):
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
            change_vpn()
            trials = trials + 1
            if trials > 5:
                PRINT_ERR("exiting")
                sys.exit(1)
            else:
                continue

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
        break

def update_US_stock_fin_information_data(db, mysql_engine, fin, stk):
    if not isinstance(fin, dict):
        return

    try:
        for stmt_type in fin.keys():
            if 'currency_symbol' in fin[stmt_type].keys():
                del fin[stmt_type]['currency_symbol']
            for duration in fin[stmt_type].keys():
                stmt = pd.DataFrame(fin[stmt_type][duration]).transpose().sort_index()
                if not stmt.empty:
                    if 'currency_symbol' in stmt.keys():
                        del stmt['currency_symbol']
                    stmt.insert(loc=0, column='Symbol', value=stk['bscs']['symbol'])
                    stmt.rename(columns={'date':'Date'}, inplace=True)

                    table_name = stmt_type+'_'+duration
                    if mysql_exists_table(mysql_engine, table_name):
                        query = 'select `Date` from {} where Symbol = \'{}\''.format(table_name, stk['bscs']['symbol'])
                        ddf = read_from_sql(query, mysql_engine)

                        #index = stmt.index.difference(ddf.index)
                        #index = stmt.index.get_loc(ddf['Date'][-1])
                        index = stmt.index.difference(ddf['Date'])
                        stmt = stmt.loc[index]

                    if not stmt.empty:
                        print("Updating %s data for %s: %r" %(table_name, stk['bscs']['symbol'], ', '.join(stmt.index.tolist())))
                        mysql_update_table(mysql_engine, table_name, stmt, check=True, insert=True, unknown_table=False, fin_table=True, cols_type='fin', temp=False, date_column=False, format_columns=False, primary_key=False)

    finally:
        update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.fin_statements_pull_date', dt.combine(dt.now(), dt.min.time()))
 
def update_US_stock_fin_information(stk, core, sem):

    aff = 0 | 1 << core
    #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
    #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    try:
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Fin')
        c  = open_db_client()
        db = c['Stocks']

        #table_name = 'Balance_Sheet_quarterly' 
        #if mysql_exists_table(mysql_engine, table_name):
        #    query = 'select `Date` from {} where Symbol = \'{}\''.format(table_name, stk['bscs']['symbol'])
        #    ddf = read_from_sql(query, mysql_engine)
        #    if not ddf.empty:
        #        return

        url='https://eodhistoricaldata.com/api/fundamentals/'+stk['bscs']['symbol']+'.US?api_token='+get_eod_token_id()+'&filter=Financials'
        try:
            ret = requests.get(url)
            if ret.status_code != 200:
                print("Failed to get financial statements for %r, error code: %r" %(stk['bscs']['symbol'], ret.status_code))
                return
        except Exception as E:
            print("Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
            return

        fin = ret.json()
        update_US_stock_fin_information_data(db, mysql_engine, fin, stk)

        #if not isinstance(fin, dict):
        #    return

        #for stmt_type in fin.keys():
        #    if 'currency_symbol' in fin[stmt_type].keys():
        #        del fin[stmt_type]['currency_symbol']
        #    for duration in fin[stmt_type].keys():
        #        stmt = pd.DataFrame(fin[stmt_type][duration]).transpose().sort_index()
        #        if not stmt.empty:
        #            if 'currency_symbol' in stmt.keys():
        #                del stmt['currency_symbol']
        #            stmt.insert(loc=0, column='Symbol', value=stk['bscs']['symbol'])
        #            stmt.rename(columns={'date':'Date'}, inplace=True)

        #            table_name = stmt_type+'_'+duration
        #            if mysql_exists_table(mysql_engine, table_name):
        #                query = 'select `Date` from {} where Symbol = \'{}\''.format(table_name, stk['bscs']['symbol'])
        #                ddf = read_from_sql(query, mysql_engine)

        #                #index = stmt.index.difference(ddf.index)
        #                #index = stmt.index.get_loc(ddf['Date'][-1])
        #                index = stmt.index.difference(ddf['Date'])
        #                stmt = stmt.loc[index]

        #            if not stmt.empty:
        #                print("Updating %s data for %s: %r" %(table_name, stk['bscs']['symbol'], ', '.join(stmt.index.tolist())))
        #                mysql_update_table(mysql_engine, table_name, stmt, check=True, insert=True, unknown_table=False, fin_table=True, cols_type='fin', temp=False, date_column=False, format_columns=False, primary_key=False)

    finally:
        if sem:
            sem.release()
        close_sql_connection(mysql_engine)
        close_db_client(c)

def update_US_all_stock_fin_information():
    c  = open_db_client()
    db = c['Stocks']

    num_processes = 6 #* 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    sort = [1, -1][dt.now().day % 2 == 0]
    j=0
 
    #syms = {"$nin" : s}
    #stocks_list = db.US_Stocks_List.find({"symbol":syms}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #stocks = db.US_Stocks.find({'bscs.symbol':'DNI'}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #stocks = db.US_Stocks.find({'General.Exchange':{"$in":major_exchanges}}).batch_size(10).sort([["sno",1]]).allow_disk_use(True)
    stocks = db.US_Stocks.find({\
                                "$and": [\
                                        #{"dates.fin_statements_pull_date": {"$exists": False}},\
                                        {'General.Exchange':{"$in":major_exchanges}},\
                                        {"General.IsDelisted": False},\
                                        {'General.Type':'Common Stock'},\
                                        ]\
                                }, no_cursor_timeout=True).sort([["General.Code",sort]]).allow_disk_use(True)
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r" %(i, stk['bscs']['symbol']))
        sem.acquire()
        #update_US_stock_fin_information(stk, 0, sem)
        processes[j%num_processes] = multiprocessing.Process(target=update_US_stock_fin_information, args=(stk, i%num_cores, sem))
        processes[j%num_processes].start()
        j = j + 1

    for j in range(len(processes)):
        if processes[j] is not None:
            processes[j].join()
 
    close_db_client(c)

def update_short_interests(stk, core, sem=None):

    aff = 0 | 1 << core
    #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
    #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    update = False
    df  = pd.DataFrame()
    rdf = pd.DataFrame()
    try:
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Short_Interests')
        c  = open_db_client()
        db = c['Stocks']

        if 'dates' in stk.keys() and \
                'short_interests_pull_date' in stk['dates'].keys() and \
                stk['dates']['short_interests_pull_date'].date() == dt.now().date():
            update = False
            return

        table_name = get_symbol_table_name(stk['bscs']['symbol'])

        if mysql_exists_table(mysql_engine, table_name) and \
                'Short_Interest_Ratio' in mysql_get_columns_from_engine(mysql_engine, table_name):
            query = 'select Date, Short_Interest_Ratio from ' + table_name + ' order by Date DESC limit 1'
            rdf = read_from_sql(query, mysql_engine)
 
        #short_interest
        url='https://eodhistoricaldata.com/api/shorts/'+stk['bscs']['symbol']+'.US?api_token='+get_eod_token_id()

        if not rdf.empty:
            url = url + \
                    '&from='+ \
                    str(dt.strptime(rdf['Date'][0], "%Y-%m-%d").date() + timedelta(1))
 
        try:
            ret = requests.get(url)
            if ret.status_code == 402:
                print("%r" %(ret.text))
                close_sql_connection(mysql_engine)
                close_db_client(c)
                sys.exit(1)
            if ret.status_code == 404:
                print("Failed to get Dividends data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                update = True
                return
            if ret.status_code != 200:
                print("Failed to get Short Interest for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                return
        except Exception as E:
            print("Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
            return

        df = pd.read_csv(StringIO(ret.text), skipfooter=1, parse_dates=[0], index_col=0, engine='python')

        df = df.dropna()
        if not df.empty:
            df['Short_Interest_Ratio'] = df[df['Volume'] != 0]['Short']/df[df['Volume'] != 0]['Volume']
            mysql_update_table(mysql_engine, table_name, df, check=True, insert=True, unknown_table=False, cols_type='price', temp=False, date_column=True, format_columns=False, primary_key=True, empty_table=False, fin_table=False)
        update = True
 
    finally:
        if update:
            update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.short_interests_pull_date', dt.combine(dt.now(), dt.min.time()))
            if not df.empty:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'Ratios.Short_Interest_Ratio', df.iloc[-1]['Short_Interest_Ratio'])
            elif not rdf.empty:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'Ratios.Short_Interest_Ratio', rdf.iloc[-1]['Short_Interest_Ratio'])
            else:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'Ratios.Short_Interest_Ratio', nan)
        if sem:
            sem.release()
        close_sql_connection(mysql_engine)
        close_db_client(c)

def update_all_short_interests():
    c  = open_db_client()
    db = c['Stocks']

    num_processes = 6 #* 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    sort = [1, -1][dt.now().day % 2 == 0]
    j=0
 
    today = dt.combine(dt.now(), dt.min.time())

    #stocks = db.US_Stocks.find({"bscs.symbol":'BRQS'})
    #stocks = db.US_Stocks.find({"General.Exchange":'NASDAQ'})
    #stocks = db.US_Stocks.find({"$and": [{"dates.short_interests_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":['NASDAQ']}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
    stocks = db.US_Stocks.find({\
                                "$and": [\
                                            {'General.Exchange':{"$in":['NASDAQ']}},\
                                            {'General.Type':'Common Stock'},\
                                            {"$or":[\
                                                    {"dates.short_interests_pull_date": {"$exists": False}},\
                                                    {"dates.short_interests_pull_date": {"$lte": get_previous_trading_day()}},\
                                                    ]\
                                            },\
                                        ]\
                                }, no_cursor_timeout=True).sort([["sno",sort]]).allow_disk_use(True)
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r" %(i, stk['bscs']['symbol']))
        sem.acquire()
        #update_short_interests(stk, 0, sem)
        processes[j%num_processes] = multiprocessing.Process(target=update_short_interests, args=(stk, i%num_cores, sem))
        processes[j%num_processes].start()
        j = j + 1

    for j in range(len(processes)):
        if processes[j] is not None:
            processes[j].join()
 
    close_db_client(c)

def update_splits(stk, core, sem=None):

    aff = 0 | 1 << core
    #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
    #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    update = False
    df  = pd.DataFrame()
    rdf = pd.DataFrame()
    try:
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Fin')
        c  = open_db_client()
        db = c['Stocks']

        if 'dates' in stk.keys() and 'splits_pull_date' in stk['dates'].keys() and \
                stk['dates']['splits_pull_date'].date() == dt.now().date():
            update = False
            return

        table_name = 'Splits_History'

        if mysql_exists_table(mysql_engine, table_name):
            query = 'select * from '+table_name +' where Symbol = \'{}\' order by Date DESC limit 1'.format(stk['bscs']['symbol'])
            rdf = read_from_sql(query, mysql_engine)
 
        url='https://eodhistoricaldata.com/api/splits/'+stk['bscs']['symbol']+'.US?api_token='+get_eod_token_id()

        if not rdf.empty:
            url = url + \
                    '&from='+ \
                    str(dt.strptime(rdf['Date'][0], "%Y-%m-%d").date() + timedelta(1))
 
        try:
            ret = requests.get(url)
            if ret.status_code != 200:
                print("Failed to get Splits data for %r, error code: %r" %(stk['bscs']['symbol'], ret.status_code))
                return
        except Exception as E:
            print("Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
            return

        df = pd.read_csv(StringIO(ret.text), skipfooter=1, parse_dates=[0], index_col=0, engine='python')

        update = True
        df = df.dropna()
        if not df.empty:
            df['Symbol'] = stk['bscs']['symbol']
            df['Split_Num']=nan
            df['Split_Denom']=nan
            for i, d in df.iterrows():
                df.loc[i, 'Split_Num']   = float(d['Stock Splits'].split('/')[0])
                df.loc[i, 'Split_Denom'] = float(d['Stock Splits'].split('/')[1])

            del df['Stock Splits']

            mysql_update_table(mysql_engine, table_name, df, check=True, insert=True, unknown_table=False, cols_type='price', temp=False, date_column=True, format_columns=False, primary_key=False, empty_table=False, fin_table=True)
 
    finally:
        if update:
            update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.splits_pull_date', dt.combine(dt.now(), dt.min.time()))
            if not df.empty:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.last_split_date', df.iloc[-1]['Date'])
            elif not rdf.empty:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.last_split_date', dt.strptime(rdf.iloc[-1]['Date'], "%Y-%m-%d"))
            else:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.last_split_date', dt.min)
        if sem:
            sem.release()
        close_sql_connection(mysql_engine)
        close_db_client(c)

def update_all_splits():
    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Fin')
    table_name = 'Splits_History'

    num_processes = 6 #* 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    sort = [1, -1][dt.now().day % 2 == 0]
    j=0

    today = dt.combine(dt.now(), dt.min.time())

    # First get splits for all new stocks
    stocks = db.US_Stocks.find({"$and": [{'General.Type':'Common Stock'}, {"dates.splits_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",sort]]).allow_disk_use(True)
    #stocks = db.US_Stocks.find({"$and": [{'General.Type':'Common Stock'}, {"$or":[{"dates.splits_pull_date": {"$lt": today}}, {"dates.splits_pull_date": {"$exists": False}}]}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
    #stocks = db.US_Stocks.find({"bscs.symbol":'BRQS'})
    #stocks = db.US_Stocks.find({"General.Exchange":'NASDAQ'})
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r" %(i, stk['bscs']['symbol']))
        sem.acquire()
        #update_splits(stk, 0, sem)
        processes[j%num_processes] = multiprocessing.Process(target=update_splits, args=(stk, i%num_cores, sem))
        processes[j%num_processes].start()
        j = j + 1

    for j in range(len(processes)):
        if processes[j] is not None:
            processes[j].join()

    # Now get the bulk list of stocks with the splits.
    # For each stock, perform update_splits().
    # This is required because the bulk pull does not return information like recorded date etc.
    # It only returns the split factor.

    url='https://eodhistoricaldata.com/api/eod-bulk-last-day/US?api_token='+get_eod_token_id()+'&type=splits'
    ret = requests.get(url)
    df  = pd.read_csv(StringIO(ret.text), skipfooter=1, parse_dates=[0], index_col=0, engine='python')
    df  = df.dropna()
    if not df.empty:
        df['Symbol'] = df.index
        if 'currency' in df.columns:
            del df['currency']
        if 'Ex' in df.columns:
            del df['Ex']
        if 'date' in df.columns:
            df.rename(columns = {'date': 'Date'}, inplace=True)
        if 'Split' in df.columns:
            df.rename(columns = {'Split': 'Stock Splits'}, inplace=True)

        df['Split_Num']=nan
        df['Split_Denom']=nan
        for i, d in df.iterrows():
            stocks = db.US_Stocks.find({"$and":[{"bscs.symbol":d['Symbol']}, {"General.Type":"Common Stock"}, {'General.Exchange':{"$in":major_exchanges}}, {"dates.splits_pull_date": {"$lt": get_latest_trading_day()}}]})
            if stocks.count() == 0 or stocks.count() > 1:
                continue

            update_splits(stocks[0], 0, sem=None)

            #df.loc[i, 'Split_Num']   = float(d['Stock Splits'].split('/')[0])
            #df.loc[i, 'Split_Denom'] = float(d['Stock Splits'].split('/')[1])

            #stk_df = df[df['Symbol'] == d['Symbol']]
            #stk_df.index = stk_df['Date']
            #del stk_df['Stock Splits']
            #mysql_update_table(mysql_engine, table_name, stk_df, insert=True, check=True, date_column=False, format_columns=False)
            #update_field(db.US_Stocks, d['Symbol'], 'dates.splits_pull_date', dt.combine(dt.now(), dt.min.time()))
            #update_field(db.US_Stocks, d['Symbol'], 'dates.last_split_date', dt.strptime(stk_df.iloc[-1]['Date'], "%Y-%m-%d"))
        del df['Stock Splits']
        
    close_db_client(c)
    close_sql_connection(mysql_engine)

def update_dividends(stk, core, sem=None):

    aff = 0 | 1 << core
    #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
    #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    update = False
    df  = pd.DataFrame()
    rdf = pd.DataFrame()
    try:
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Fin')
        c  = open_db_client()
        db = c['Stocks']

        if 'dates' in stk.keys() and 'dividends_pull_date' in stk['dates'].keys() and \
                stk['dates']['dividends_pull_date'].date() == dt.now().date():
            update = False
            return

        table_name = 'Dividends_History'

        if mysql_exists_table(mysql_engine, table_name):
            query = 'select * from '+table_name +' where Symbol = \'{}\' order by Date DESC limit 1'.format(stk['bscs']['symbol'])
            rdf = read_from_sql(query, mysql_engine)
 
        url='https://eodhistoricaldata.com/api/div/'+stk['bscs']['symbol']+'.US?api_token='+get_eod_token_id()

        if not rdf.empty:
            url = url + \
                    '&from='+ \
                    str(dt.strptime(rdf['Date'][0], "%Y-%m-%d").date() + timedelta(1))
        url = url + '&fmt=json'
 
        try:
            ret = requests.get(url)
            if ret.status_code == 402:
                print("%r" %(ret.text))
                close_sql_connection(mysql_engine)
                close_db_client(c)
                sys.exit(1)
            if ret.status_code == 404:
                print("Failed to get Dividends data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                update = True
                return
            if ret.status_code != 200:
                print("Failed to get Dividends data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                return
        except Exception as E:
            print("Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
            return

        dividends = ret.json()
        if len(dividends) == 0:
            update = True
            return

        df = pd.DataFrame(dividends)
        if not df.empty:
            df['Symbol'] = stk['bscs']['symbol']
            if 'currency' in df.columns:
                del df['currency']
            if 'Ex' in df.columns:
                del df['Ex']
            if 'date' in df.columns:
                df.rename(columns = {'date': 'Date'}, inplace=True)

            mysql_update_table(mysql_engine, table_name, df, check=True, insert=True, unknown_table=False, cols_type='dividends', temp=False, date_column=False, format_columns=False, primary_key=False, empty_table=False, fin_table=True)
            update = True
 
    finally:
        if update:
            update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.dividends_pull_date', dt.combine(dt.now(), dt.min.time()))
            if not df.empty:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.last_dividend_date', dt.strptime(df.iloc[-1]['Date'], "%Y-%m-%d"))
            elif not rdf.empty:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.last_dividend_date', dt.strptime(rdf.iloc[-1]['Date'], "%Y-%m-%d"))
            else:
                update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.last_dividend_date', dt.min)
        if sem:
            sem.release()
        close_sql_connection(mysql_engine)
        close_db_client(c)

def update_all_dividends():
    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Fin')
    table_name = 'Dividends_History'
    sort = [1, -1][dt.now().day % 2 == 0]

    num_processes = 6 #* 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    j=0
 
    today = dt.combine(dt.now(), dt.min.time())

    try:
        # First get dividends for all new stocks
        stocks = db.US_Stocks.find({"$and": [{'General.Type':'Common Stock'}, {"dates.dividends_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",sort]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and": [{"dates.dividends_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and": [{"dates.dividends_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and": [{"$or":[{"dates.dividends_pull_date": {"$lt": today}}, {"dates.dividends_pull_date": {"$exists": False}}]}, {'General.Exchange':{"$in":major_exchanges}}, {'General.Type':'Common Stock'}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"bscs.symbol":'ATCO'})
        #stocks = db.US_Stocks.find({"General.Exchange":{'$in': major_exchanges}})
        print(stocks.count())

        for i, stk in enumerate(stocks):
            print("%d: %r" %(i, stk['bscs']['symbol']))
            sem.acquire()
            #update_dividends(stk, 0, sem)
            processes[j%num_processes] = multiprocessing.Process(target=update_dividends, args=(stk, i%num_cores, sem))
            processes[j%num_processes].start()
            j = j + 1

        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()

        url='https://eodhistoricaldata.com/api/eod-bulk-last-day/US?api_token='+get_eod_token_id()+'&type=dividends&fmt=json'
        ret = requests.get(url)
        if ret.status_code != 200:
            return

        df  = pd.DataFrame(ret.json())
        df  = df.dropna()
        if not df.empty:
            if 'code' in df.columns:
                df.rename(columns = {'code': 'Symbol'}, inplace=True)
            if 'currency' in df.columns:
                del df['currency']
            if 'Ex' in df.columns:
                del df['Ex']
            if 'exchange' in df.columns:
                del df['exchange']
            if 'date' in df.columns:
                df.rename(columns = {'date': 'Date'}, inplace=True)
            if 'dividend' in df.columns:
                df.rename(columns = {'dividend': 'value'}, inplace=True)
            df.index = df['Date']

            for i, d in df.iterrows():
                stocks = db.US_Stocks.find({"$and":[{"bscs.symbol":d['Symbol']}, {"General.Type":"Common Stock"}, {'General.Exchange':{"$in":major_exchanges}}, {"dates.dividends_pull_date": {"$lt": get_latest_trading_day()}}]})

                if stocks.count() == 0 or stocks.count() > 1:
                    continue
                update_dividends(stocks[0], 0, sem=None)

                #stk_df = df[df['Symbol'] == d['Symbol']]
                #mysql_update_table(mysql_engine, table_name, stk_df, insert=True, check=True, date_column=False, format_columns=False)
                #update_field(db.US_Stocks, d['Symbol'], 'dates.dividends_pull_date', dt.combine(dt.now(), dt.min.time()))
                #update_field(db.US_Stocks, d['Symbol'], 'dates.last_dividend_date', dt.strptime(stk_df.iloc[-1]['Date'], "%Y-%m-%d"))
 
    finally:
        close_db_client(c)
        close_sql_connection(mysql_engine)

def update_technicals(stk, core=None, sem=None, general_only=False, ratelimit_event=None, lock=None):
    global technicals_ratelimit_reset_time

    if core:
        aff = 0 | 1 << core
        #print("%s: Pid: %r, Core: %r, new_aff: %r" %(stk['bscs']['symbol'], os.getpid(), core, aff))
        #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
        os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    # Reached max number of APIs per minute.
    # Wait till 60 sec and try.
    if ratelimit_event and ratelimit_event.is_set() is False:
        print("%s: ratelimit_event set, waiting "%(stk['bscs']['symbol']))
        ratelimit_event.wait()
        print("%s: ratelimit_event cleared, waking up "%(stk['bscs']['symbol']))

    update = False
    df  = pd.DataFrame()
    try:
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Technicals')
        c  = open_db_client()
        db = c['Stocks']

        if 'dates' in stk.keys() and 'technicals_pull_date' in stk['dates'].keys() and \
                stk['dates']['technicals_pull_date'].date() == dt.now().date():
            update = False
            return

        table_name = get_symbol_table_name(stk['bscs']['symbol'])

        #url='https://eodhistoricaldata.com/api/fundamentals/'+stk['bscs']['symbol']+'?api_token='+get_eod_token_id()+'&filter=General'

        #try:
        #    ret = requests.get(url)
        #    if ret.status_code == 402:
        #        print("%r" %(ret.text))
        #        close_sql_connection(mysql_engine)
        #        close_db_client(c)
        #        sys.exit(1)

        #    if ret.status_code == 404:
        #        print("Failed to get Technical data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
        #        update = True
        #        return
        #    if ret.status_code != 200:
        #        print("Failed to get Technical data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
        #        return
        #except Exception as E:
        #    print("Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
        #    return

        #technicals = ret.json()
        #if len(technicals) == 0 or not isinstance(technicals, dict):
        #    update = True
        #    return

        #db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {'General': technicals}})
 
        if general_only == True:
            url='https://eodhistoricaldata.com/api/fundamentals/'+stk['bscs']['symbol']+'?api_token='+get_eod_token_id()+'&filter=General'
        else:
            url='https://eodhistoricaldata.com/api/fundamentals/'+stk['bscs']['symbol']+'?api_token='+get_eod_token_id()+'&filter=General,Highlights,Valuation,SharesStats,Technicals,SplitsDividends,AnalystRatings,Financials'

        try:
            while True:
                ret = requests.get(url)
                if ret.status_code == 402:
                    print("%s: Ratelimit: %r, %r" %(stk['bscs']['symbol'], int(ret.headers['X-RateLimit-Remaining']), ret.text))
                    close_sql_connection(mysql_engine)
                    close_db_client(c)
                    sys.exit(1)
                elif ret.status_code == 404:
                    print("Failed to get Technical data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                    update = True
                    return
                elif ret.status_code != 200:
                    print("Failed to get Technical data for %r, error code: %r, error: %r" %(stk['bscs']['symbol'], ret.status_code, ret.text))
                    return
                elif ratelimit_event and int(ret.headers['X-RateLimit-Remaining']) == 0:
                    now = dt.now()
                    # If the ratelimit was not yet reset,
                    # wait for 60 secs
                    if technicals_ratelimit_reset_time is None: 
                        secs = 60
                    else:
                        # Because the ratelimit is restricted 
                        # 1000 requests per minute, wait for 
                        # 60 - number of seconds elapsed since the 
                        # ratelimit was reset. We don't need to wait
                        # again for 60 secs.
                        secs = 60 - (now-technicals_ratelimit_reset_time).seconds

                    lock_acquired = unblocked_lock(lock)
                    # I am the first process to know that ratelimit has reached.
                    # Tell the other processes to wait and not send any further API requests.
                    # Sleep for the remaining time.
                    # Reset the ratelimit time to now.
                    # Wakeup and inform the other processes to resume.
                    if lock_acquired:
                        print("%s: Broadcasting ratelimit reached" %(stk['bscs']['symbol']))
                        ratelimit_event.clear()
                        print("%s: Reached max limit, waiting for %s sec"%(stk['bscs']['symbol'], sec))
                        time.sleep(secs)
                        technicals_ratelimit_reset_time = dt.now()
                        print("%s: Broadcasting ratelimit reset" %(stk['bscs']['symbol']))
                        ratelimit_event.set()
                        lock.release()
                    else:
                        # I am not the first one to know that the ratelimit has reached.
                        # The first guy has already informed the other processes
                        # who have not yet sent the API requests to wait.
                        # Unfortunately I came to know a bit late.
                        # I will simply wait for the remaining time.
                        print("%s: Reached max limit, waiting without lock for %s sec"%s(stk['bscs']['symbol'], sec))
                        time.sleep(secs)
                    # Now retry the API request again.
                    continue
                else:
                    break
        except Exception as E:
            print("Symbol: %r, exception : %r" %(stk['bscs']['symbol'], str(E)))
            return

        technicals = ret.json()
        if len(technicals) == 0 or not isinstance(technicals, dict):
            update = True
            return

        # Update general information
        if 'General' in technicals.keys():
            db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {'General': technicals['General']}})
            del technicals['General']
        
        # Update financial sheets
        if 'Financials' in technicals.keys():
            update_US_stock_fin_information_data(db, mysql_engine, technicals['Financials'], stk)
            del technicals['Financials']

        if general_only == True:
            return

        df = pd.DataFrame()
        for k in technicals.keys():
            if technicals[k] != 'NA':
                df = pd.concat([df, pd.DataFrame.from_dict(technicals[k], orient='index')])
                db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {k: technicals[k]}})

        if not df.empty:
            if 'NumberDividendsByYear' in df.index:
                df.drop(['NumberDividendsByYear'], inplace=True)

            df = df.transpose()
            df['Date'] = get_latest_trading_day().date()
            df.index = df['Date']
            # Remove duplicate columns
            df = df.loc[:,~df.columns.duplicated()]

            mysql_update_table(mysql_engine, table_name, df, check=True, insert=True, unknown_table=False, cols_type='general', temp=False, date_column=False, format_columns=False, primary_key=True, empty_table=False, fin_table=False)
            update = True
 
    finally:
        if update:
            update_field(db.US_Stocks, stk['bscs']['symbol'], 'dates.technicals_pull_date', dt.combine(dt.now(), dt.min.time()))
        if sem:
            sem.release()
        close_sql_connection(mysql_engine)
        close_db_client(c)

def update_all_technicals():

    c  = open_db_client()
    db = c['Stocks']
    ratelimit_event = multiprocessing.Event()
    ratelimit_event.set()
    lock = multiprocessing.Lock()
    general_only=False

    num_processes = num_cores #* 4
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes
    sort = [1, -1][dt.now().day % 2 == 0]
    j=0
 
    today = dt.combine(dt.now(), dt.min.time())

    # Get trading symbols from eod
    df = get_eod_all_trading_symbols(exchanges=major_exchanges, quoteType='Common Stock')

    # Get already updated stocks list
    stks = db.US_Stocks.find({'dates.technicals_pull_date':{'$gte':get_latest_trading_day()}} ,{"bscs.symbol":1, '_id':False}).batch_size(10).sort([["General.Code",sort]]).allow_disk_use(True)
    syms=[]
    for stk in stks:
        syms.append(stk['bscs']['symbol'])

    stk_df=pd.DataFrame(syms, columns=['Symbol'])

    # Get list of symbols to be updated
    df = df[~df.Symbol.isin(stk_df.Symbol)]
    print("Total Symbols: %r" %(len(df)))

    try:
        # First get dividends for all new stocks
        #stocks = db.US_Stocks.find({"$and": [{'General.Type':'Common Stock'}, {"dates.dividends_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and": [{"dates.dividends_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and": [{"dates.dividends_pull_date": {"$exists": False}}, {'General.Exchange':{"$in":major_exchanges}}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and": [{"$or":[{"dates.technicals_pull_date": {"$lte": get_previous_trading_day()}}, {"dates.technicals_pull_date": {"$exists": False}}]}, {'General.Exchange':{"$in":major_exchanges}}, {'General.Type':'Common Stock'}]}, no_cursor_timeout=True).sort([["sno",1]]).allow_disk_use(True)
        #stocks = db.US_Stocks.find({"$and":[{"General":{"$exists":False}}, {'General.Exchange':{"$in":major_exchanges}}]})
        #stocks = db.US_Stocks.find({"$and":[{"General.Exchange":{'$in': major_exchanges}}, {'General.Type':'Common Stock'}, {"dates.technicals_pull_date": {"$lt": get_latest_trading_day()}}]}).batch_size(10).sort([["sno",1]]).allow_disk_use(True)

        #stocks = db.US_Stocks.find({"General":{"$exists":False}})
        #print(stocks.count())

        #for i, stk in enumerate(stocks):
        #    print("%d: %r" %(i, stk['bscs']['symbol']))
        #    sem.acquire()
        #    #update_technicals(stk, 0, sem)
        #    processes[j%num_processes] = multiprocessing.Process(target=update_technicals, args=(stk, i%num_cores, sem))
        #    processes[j%num_processes].start()
        #    j = j + 1

        i = 0
        skip = 0
        for sym, d in df.iterrows():
            stks = db.US_Stocks.find({'bscs.symbol': sym})
            if stks.count() == 0:
                add_symbol_to_database(d, db)
                # Pull the updated data
                stks = db.US_Stocks.find({'bscs.symbol': sym})
            stk = stks[0]

            ## Already updated skip
            #if stk['dates']['technicals_pull_date'] >= get_latest_trading_day():
            #    print("%r: %r skipping" %(skip, stk['bscs']['symbol']))
            #    skip = skip+1
            #    continue
            sem.acquire()
            print("%d: %r" %(i, stk['bscs']['symbol']))
            #update_technicals(stk, None, sem)
            processes[j%num_processes] = multiprocessing.Process(target=update_technicals, args=(stk, i%num_cores, sem, general_only, ratelimit_event, lock))
            processes[j%num_processes].start()
            j = j + 1
            i = i + 1

    finally:
        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()

        set_sno('US')

        print("Skipped: %r, Updated: %r" %(skip, i))
        close_db_client(c)

def update_US_holiday_list():
    ret = False
    start = date(date.today().year, 1, 1)
    end = date(date.today().year,12,31)
    url='https://eodhistoricaldata.com/api/exchange-details/US?api_token='+\
            get_eod_token_id()+\
            '&from='+str(start)+\
            '&to='+str(end)
    try:
        ret = requests.get(url)
        if ret.status_code != 200:
            print("Failed to get the US holiday list")
            return
    except Exception as E:
        print("Failed to get the US holiday list. Error: %r"%(str(E)))
  
    try:
        df = pd.DataFrame(ret.json()['ExchangeHolidays']).transpose()
        df.index = df['Date']
        mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks_Data')
        table_name = 'US_Holiday_List'
        mysql_check_n_create_table(mysql_engine, table_name)
        query = 'select * from {}'.format(table_name)
        ddf = read_from_sql(query, mysql_engine)
        df = df_difference(df, ddf)
        if not df.empty:
            mysql_update_table(mysql_engine, table_name, df, check=True, insert=True, unknown_table=False, cols_type='generic', temp=False, date_column=False, format_columns=False, primary_key=True, empty_table=False)
        ret = True
    finally:
        close_sql_connection(mysql_engine)
        return ret

# This function is deprecated. Instead use build_US_stock_information2
def build_US_stock_information(doc, finance=True):
    c    = open_db_client()
    db   = c['Stocks']
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
        if 'etf' in doc['Name'].lower() or 'fund' in doc['Name'].lower():
            stock = {}
            ret = parse_html.populate_US_stocks(db, None, None, stock, sym, name, etf=True) 
        elif finance == False:
            stock = {}
            ret = parse_html.populate_US_stocks(db, None, None, stock, sym, name, etf=False) 
        else:
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
                ret = parse_html.populate_US_stocks(db, root, files, stock, sym, name) 
                #ret = parse_html.populate_US_stocks(db, root, files, stock, sym, name, doc['Sector'], doc['Industry']) 
            if ret is True:
                db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"data": "YES"}})
                #write_stock_to_file(doc['symbol'], "stocks.txt", "a")
                remove_dir(path)
    db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})

def build_US_stock_information2(doc):
    c    = open_db_client()
    db   = c['Stocks']
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
        if 'etf' in doc['Name'].lower() or 'fund' in doc['Name'].lower():
            stock = {}
            ret = parse_html.populate_US_stocks(db, None, None, stock, sym, name, etf=True) 
        elif finance == False:
            stock = {}
            ret = parse_html.populate_US_stocks(db, None, None, stock, sym, name, etf=False) 
        else:
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
                ret = parse_html.populate_US_stocks(db, root, files, stock, sym, name) 
                #ret = parse_html.populate_US_stocks(db, root, files, stock, sym, name, doc['Sector'], doc['Industry']) 
            if ret is True:
                db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"data": "YES"}})
                #write_stock_to_file(doc['symbol'], "stocks.txt", "a")
                remove_dir(path)
    db.US_Stocks_List.update({'symbol': doc['symbol']}, {'$set': {"parsed": "YES"}})

def build_US_all_stock_information():
    j=0
    c  = open_db_client()
    db = c['Stocks']

    #s=[]
    #f = open("stocks.txt","r")
    #for line in f:
    #    line = line.replace("\n","")
    #    s.append(line)
    #if len(s) > 0:
    #    del s[-1]
    #syms = {"$nin" : s}
    #stocks_list = db.US_Stocks_List.find({"symbol":syms}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    stocks_list = db.US_Stocks_List.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #stocks_list = db.US_Stocks_List.find({'parsed':'NO'},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #print("Number of stocks not yet parsed: %r" %(stocks_list.count()))

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

            build_US_stock_information2(doc)
            #build_US_stock_information(doc, finance=False)

    #set_sno('US')
    # Create index based on sno
    #db.US_Stocks.createIndex({sno: -1})
    #db.US_Stocks.createIndex({ "$**": "text" },{ name: "TextIndex" })

    print("Total : %d" %(j))
    close_db_client(c)

#Update sector and industry info in the database for each stock from the US_List database
def update_sector_info():
    c  = open_db_client()
    db = c['Stocks']

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
    close_db_client(c)

def get_beta(country, sym, sdate, edate, df=None, recession=False):
    betas = {}
    sql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    if df is None:
        try:
            query = 'select Date, `Adj Close` from {} where Date between \'{}\' and \'{}\''.format(get_symbol_table_name(sym), sdate.strftime("%Y-%m-%d"), edate.strftime("%Y-%m-%d"))
            df = read_from_sql(query, sql_engine)

            if df.empty:
                close_sql_connection(sql_engine)
                return betas
            ##from pandas_datareader.quandl import QuandlReader
            ##df = pdr.get_data_stooq(sym, sdate, edate, retry_count=3)
            ##print(df)
            ##df = hdf5.get_dataframe(country, sym, sdate, edate)
            #df = hdf5.read_from_hdf(country, sym, sdate, edate)
        except Exception as e:
            print("Could not get data for %s. Failed to calculate beta, query: %s" %(sym, query))
            close_sql_connection(sql_engine)
            return None
    if df.empty:
        close_sql_connection(sql_engine)
        return None

    if pd.to_datetime(sdate) < df.index[0]:
        sdate = df.index[0].date()

    if pd.to_datetime(edate) < df.index[0]:
        close_sql_connection(sql_engine)
        return None

    if pd.to_datetime(edate) > df.index[-1]:
        edate = df.index[-1].date()

    if country == 'US':
        bindex = "SP500"
    elif country == 'India':
        bindex = "BSE" 
    else:
        PRINT_ERROR("Unknown country. Unable to calculate beta for %s" %(sym))
        close_sql_connection(sql_engine)
        return betas

    try:
        query = 'select Date, `Adj Close` from {} where Date between \'{}\' and \'{}\''.format(get_symbol_table_name(bindex), df.index[0].strftime("%Y-%m-%d"), df.index[-1].strftime("%Y-%m-%d"))
        dfb = read_from_sql(query, sql_engine)
        if dfb.empty:
            close_sql_connection(sql_engine)
            return betas

        ##dfb = hdf5.get_dataframe(country, bindex, df.index[0], df.index[-1])
        #dfb = hdf5.read_from_hdf(country, bindex, pd.Timestamp(df.index[0]).date(), pd.Timestamp(df.index[-1]).date())
        ##dfb = hdf5.get_dataframe(country, bindex, sdate, edate)
    except Exception as e:
        print("Could not get data for %s. Failed to calculate beta" %(bindex))
        close_sql_connection(sql_engine)
        return None
   
    # Calculate CAGR
    s_first = df['Adj Close'][0]
    if isinstance(s_first, complex):
        print("first is complex number")
    s_last = df['Adj Close'][-1]
    if isinstance(s_last, complex):
        print("last is complex number")
    #print(df['Adj Close'].head(5))
    #print(df['Adj Close'].tail(5))
    df_start_date = df.index[0].to_pydatetime().date()
    df_end_date   = df.index[-1].to_pydatetime().date()
    try:
        years = (edate-sdate).days/365.25
    except Exception:
        print("edate: %s, sdate: %s"%(edate,sdate))
        close_sql_connection(sql_engine)
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

    try:
        first = dfb['Adj Close'][0]
        last  = dfb['Adj Close'][-1]
    except IndexError as E:
        print("Exception: %s" %(E))
        return betas 

    bgrowth_percent = last/first - 1
    if years == 0:
        b_cagr = None
    else:
        b_cagr = round((((last/first)**(1/years))-1), 4)
    #print("Years: %r, first: %r, last: %r, cagr: %r, cagr_b: %r" %(round(years,2), first, last, round(cagr,4), round(b_cagr,4)))

    # from daily data points, create a time-series of monthly data points
    if df_end_date-df_start_date <= timedelta(days=31):
        duration='d'
        if df_end_date == df_start_date:
            time_period = 1
        else:
            time_period = 31/(df_end_date-df_start_date).days * 12
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
    momentum = np.prod(1+dfsm["s_returns"].tail(12).values) -1
    
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
    betas.update({"Start_Date":dt.combine(df.index[0].date(), dt.min.time())})
    betas.update({"End_Date": dt.combine(df.index[-1].date(), dt.min.time())})
    betas.update({"Index_CAGR":b_cagr})
    betas.update({"Index_Percent_Change":bgrowth_percent})
    betas.update({"CAGR":cagr})
    betas.update({"Percent_Change":growth_percent})
    betas.update({"beta":beta})
    betas.update({"alpha":alpha})
    betas.update({"alpha_pure":alpha_pure})
    betas.update({"r_squared":r_squared})
    betas.update({"volatility":volatility})
    betas.update({"momentum":momentum})
    betas.update({"avg_price":df['Adj Close'].mean()})
    #print(betas)

    # Only for recession betas
    #if edate != dt.now().date():
    if recession:
        try:
            query = 'select Date, `Adj Close` from {} where Date between \'{}\' and NOW()'.format(get_symbol_table_name(sym), df.index[-1].strftime("%Y-%m-%d"))
            df = read_from_sql(query, sql_engine)
            ##from pandas_datareader.quandl import QuandlReader
            ##df = pdr.get_data_stooq(sym, sdate, edate, retry_count=3)
            ##print(df)
            #df = hdf5.read_from_hdf(country, sym, edate)
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
            query = 'select Date, `Adj Close` from {} where Date between \'{}\' and \'{}\''.format(get_symbol_table_name(sym), sdate.strftime("%Y-%m-%d"), edate.strftime("%Y-%m-%d"))
            df = read_from_sql(query, sql_engine)
            #df = hdf5.read_from_hdf(country, sym, sdate, edate)
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
 
    close_sql_connection(sql_engine)
    return betas
    #print (stock, beta, alpha, r_squared, volatility, momentum)
    
def update_stock_recession_betas(country, collection, doc, sym, df=None):
    years = recessions.keys()
    since = doc['bscs']['since']
    since_start = dt.strptime(since, "%Y-%m-%d").date()
 
    for year in years:
        try:
            #if not 'recession' in doc['fig']['betas'].keys() or not year in doc['fig']['betas']['recession'].keys():
            if True:
                #print("Recession Betas")
                st_date = dt.strptime(recessions[year]['start'], "%d %B %Y").date()
                if st_date >= since_start:
                    if 'end' in recessions[year].keys():
                        en_date = dt.strptime(recessions[year]['end'], "%d %B %Y").date()
                    else:
                        en_date = dt.now().date()
                    #print(st_date)
                    #print(en_date)
                    betas = get_beta(country, sym, st_date, en_date, df=None, recession=True)
                    #print("Beta: %r" %(betas))
                    field="fig.betas.recession.%s" %(year)
                    collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
        except KeyError:
                #print("Recession Betas")
                st_date = dt.strptime(recessions[year]['start'], "%d %B %Y").date()
                en_date = dt.strptime(recessions[year]['end'], "%d %B %Y").date()
                #print(st_date)
                #print(en_date)
                betas = get_beta(country, sym, st_date, en_date, df=None, recession=True)
                #print("Beta: %r" %(betas))
                field="fig.betas.recession.%s" %(year)
                collection.update({'bscs.symbol':sym},{'$set': {field : betas}})
    return

def update_stock_betas2(country, stk, core=0, sem=None, df=None):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    price_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    beta_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Beta')

    try:
        update_stock_betas(country, collection, price_engine, beta_engine, stk, core=core, sem=sem, df=df)
    finally:
        close_db_client(c)
        close_sql_connection(price_engine)
        close_sql_connection(beta_engine)

def add_beta_columns(sql_engine, table_name, cols):
    for b in beta_change_fields:
        if b not in cols:
            mysql_add_column(sql_engine, table_name, b, 'float', remove_spaces=False)

def get_beta_columns(beta_field):
    cols = []
    for c1 in beta_parameters:
        cols.append(beta_field+'_'+c1)

    return cols

def get_all_beta_columns():
    cols = []
    for c1 in beta_change_fields:
        for c2 in beta_parameters:
            cols.append(c1+'_'+c2)

    return cols

def update_stock_betas(country, collection, price_engine, beta_engine, stk, core=0, sem=None, df=None):
    aff = 0 | 1 << core
    #print("Setting %d's affinity to core: %d" %(os.getpid(), core))
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))
 
    try:
        sym = stk['bscs']['symbol']
        table_name = get_symbol_table_name(sym)
        
        #print("beta: %r: %r" %(stk['sno'], sym))
        if 'since' not in stk['bscs'].keys():
            mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks')
            stk  = update_since_dataframe(mysql_engine, table_name, collection, stk)
            close_sql_connection(mysql_engine)

        since = stk['bscs']['since']
        #print("since: %r" %(since))
        #sno = int(read_from_file("beta.txt"))
        #if sno > stk['sno']:
        #    continue
        since_start = dt.strptime(since, "%Y-%m-%d").date()
        
        update_stock_recession_betas(country, collection, stk, sym, df=df)
       
        #if ('since_last_recession' in stk['fig']['betas'].keys() and 
        #   stk['fig']['betas']['since_last_recession']['End_Date'].date() < dt.now().date()
        #   ):
        if True:
            #print(stk['fig']['betas'].keys())
            #Since last recession
            betas = None
            year = sorted(recessions.keys())[-1]
            #st_date = dt.strptime(recessions['2007']['end'], "%d %B %Y").date()
            # If last recession has successfully ended, calculate betas from the end date of the
            # recession. If not, that means the economy is still in recession. In that case,
            # calculate from start date of the recession.
            if 'end' in recessions[list(recessions.keys())[-1]].keys():
                st_date = dt.strptime(recessions[list(recessions.keys())[-1]]['end'], "%d %B %Y").date()
            else:
                st_date = dt.strptime(recessions[list(recessions.keys())[-1]]['start'], "%d %B %Y").date()
            en_date = dt.now().date()
            #print("Since last recession")
            #print(st_date)
            #print(en_date)
            betas = get_beta(country, sym, st_date, en_date, df=df)
            #print("Betas: %r" %(betas))
            field="fig.betas.since_last_recession"
            collection.update({'bscs.symbol':sym},{'$set': {field : betas}})

        #mysql_check_n_create_table(beta_engine, table_name)
        #metadata = MetaData()
        #table = Table(table_name, metadata, autoload=True, autoload_with=beta_engine)
        #table_cols = mysql_get_columns(table)
        #beta_cols  = get_all_beta_columns()

        #missing_cols = list(set(beta_cols)-set(table_cols))
        #if len(missing_cols) > 0:
        #    #print("%s: Adding missing columns:", %(table_name, missing_cols))
        #    miss = mysql_add_columns(beta_engine, table_name, missing_cols, 'float', remove_spaces=False)
        #    if miss > 0:
        #        PRINT_ERR("Failed to add %r columns to table %r" %(miss, table_name))
        #        PRINT_ERR("Columns: ",missing_cols)
        #        sys.exit(1)
 
        ##add_beta_columns(sql_engine, table_name, cols)
        #del metadata
        #del table


        price_db = db_name(price_engine)
        beta_db  = db_name(beta_engine)

        # Get all entries whose betas are not yet calculated
        #query = 'select `Date`, `Adj Close` from %s where `%s` is NULL order by Date' %(table_name, beta_cols[0])
        #query = 'select `Date` from %s order by Date' %(table_name)
        #beta_df = read_from_sql(query, price_engine)
        #query = 'select `Date` from %s order by Date' %(table_name)
        #beta_df = read_from_sql(query, price_engine)
        #if df.empty:
        #    return

        insert=False
        for i, field in enumerate(beta_change_fields):
            if (mysql_exists_table(beta_engine, table_name) and
                    field+'_Momentum' in mysql_get_columns_from_engine(beta_engine, table_name)):
                query = 'select Date, `Adj Close` from {}.{} WHERE Date not in (Select Date from {}.{} WHERE {} is not NULL order by Date);'.format(price_db, table_name, beta_db, table_name, field+'_Momentum')
            else:
                query = 'select Date, `Adj Close` from {}.{};'.format(price_db, table_name)
            price_df = read_from_sql(query, price_engine)
            if price_df.empty:
                continue

            #wdf = pd.DataFrame(index=price_df.index[1:], columns=['Date']+get_beta_columns(b)) 
            #wdf = pd.DataFrame(index=price_df.index[1:], columns = [b+'_'+s for s in list(betas.keys())])
            #print("%s: %s" %(sym, field))
            betas = []
            for index, d in price_df.iterrows():
            #for index, d in price_df.iloc[1:].iterrows():
                beta = None
                en_date = pd.to_datetime(index).date()
                #st_date = en_date - beta_change_fields[field]
                if field == 'Whole':
                    st_date = dt.strptime("1970-01-01", "%Y-%m-%d").date()
                else:
                    st_date = en_date - beta_change_fields[field]

                beta = get_beta(country, sym, st_date, en_date)
                betas.append(beta)

            wdf = pd.DataFrame(betas)
            wdf.index = wdf['End_Date']
            wdf.rename(columns = {'End_Date': 'Date'}, inplace=True)
            wdf = wdf[['Date']+beta_parameters]
            w_cols = ['Date'] +[field+'_'+s.capitalize() for s in beta_parameters]
            wdf.columns = w_cols
            #wdf = wdf.dropna()
            # taken care in mysql_update_table
            #wdf = wdf.where(pd.notnull(wdf), None)
                
            field="fig.betas." + field.lower()
            #field="fig.betas." + field.rsplit('_', 1)[0].lower()
            collection.update({'bscs.symbol':sym},{'$set': {field : beta}})
            mysql_update_table(beta_engine, table_name, wdf, check=True, cols_type='float', insert=insert, date_column=False, format_columns=False)
            print("%s: %r: writing Beta Done, total_rows: %r" %(table_name, field, len(price_df)))

    finally:
        update_field(collection, stk['bscs']['symbol'], 'dates.betas_calc_date', dt.combine(dt.now(), dt.min.time()))
        if sem:
            sem.release()

def update_all_stock_betas(country):
    c = open_db_client()
    db = c['Stocks']
    collection = get_collection(country, db)
    #sql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

    #docs = db.find({"$or": [{"fig.betas.recession": {"$fig.betas.since_last_recession": {"$exists": False}}, {"fig.betas.whole": {"$exists": False}}, {"fig.betas.five_year": {"$exists": False}}, {"fig.betas.one_year": {"$exists": False}}, {"fig.betas.six_months": {"$exists": False}}]}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({ "$and": [{"$or": [{"fig.betas.recession": {"$exists": False}},{"fig.betas.since_last_recession": {"$exists": False}}, {"fig.betas.whole": {"$exists": False}}, {"fig.betas.five_year": {"$exists": False}}, {"fig.betas.one_year": {"$exists": False}}, {"fig.betas.six_months": {"$exists": False}}]}, {"bscs.symbol":{"$nin" : ["AAN", "GOLF", "SFS"]}}]}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = collection.find({"fig.betas": {"$exists": False}},no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({"bscs.symbol":{"$in" : ["MKTX"]}}, no_cursor_timeout=True).sort([["sno",1]])
    #docs = db.find({"bscs.symbol":{"$nin" : ["LABL", "LEXEB", "HF", "AMBR", "AAN", "SFS", "HRS", "LLL", "CZFC", "LION", "JSYN", "LGCY", "PYDS"]}}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    #docs = collection.find({}, no_cursor_timeout=True).batch_size(3).sort([["sno",1]]).allow_disk_use(True)
    docs = collection.find({"$and":[{'General.Exchange':{"$in":major_exchanges}}, {'General.Type':'Common Stock'},{"$or":[{'dates.betas_calc_date': {"$exists": False}}, {'dates.betas_calc_date': {"$lt": get_previous_trading_day()}}]}]}, no_cursor_timeout=True).batch_size(2).sort([["failcount.mysql_price_failcount",1]]).allow_disk_use(True).sort([["sno",1]]).allow_disk_use(True)
    print("Total Stocks: %r" %(docs.count()))

    #max_threads = thread_factor
    #sem = threading.BoundedSemaphore(max_threads)
    num_processes = num_cores #* 2 
    sem = multiprocessing.BoundedSemaphore(num_processes)
    processes = [None]*num_processes

    i=0
    try:
        for i, doc in enumerate(docs):
            #if ignore_stock(doc):
            #    continue
            with open('/home/vpetla/work/stockanalysis/beta_stop.txt', 'r') as f:
                data = f.read()

            if data == 'yes\n':
                break

            sem.acquire()
            print("%r: %s" %(i, doc['bscs']['symbol']))
            #update_stock_betas2(country, copy.deepcopy(doc), 0, sem)
            processes[i%num_processes] = multiprocessing.Process(target=update_stock_betas2, args=(country, copy.deepcopy(doc), i%num_cores, sem,))
            processes[i%num_processes].start()

    finally:
        for j in range(len(processes)):
            if processes[j] is not None:
                processes[j].join()
        time.sleep(10)
        close_db_client(c)
        #close_sql_connection(sql_engine)
        print("Betas: Stocks tried :%r"%(i))
 
def set_sno(country):
    print("Updating sno for symbols")
    c  = open_db_client()
    db = c['Stocks']
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

    close_db_client(c)

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
   
    if cur_val is None:
        cur_val = nan

    if duration is None: # Whole percentage case
        start_loc = 0
        start_date = pd.to_datetime(df.index[0]).date()
    else:
        start_date = cur_date - duration
        start_loc = hdf5.get_nearest_index(df, start_date)

    if start_loc == cur_loc:
        if isnan(cur_val):
            change = nan
        else:
            change = 0
    else:
        if start_loc is None:
            start_val = nan
        else:
            # Get the first non nan value and non-zero from the set of records
            start_val = df.iloc[start_loc][c]

        if start_val is None:
            start_val = nan

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

        if start_val is None:
            start_val = nan
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
    # vpetla
    df.loc[index, key] = change
    #df[key][index] = change
    return df

def fin_change(df, fig, items=None):
    #st_price = read.iat[0, read.columns.get_loc('close')]
    #en_price = read.iat[-1, read.columns.get_loc('close')]

    #df.index= pd.to_datetime(df.index)
    if fig == 'fig':
        fields    = fin_year_fields
        datatypes = fin_year_fields_datatypes
        durations = fin_year_price_durations
        ret_index = pd.DatetimeIndex.strftime(df.index, "%Y-%m")
        reg_exp   = r'yo\S+'
    else:
        fields    = fin_quarter_fields
        datatypes = fin_quarter_fields_datatypes
        durations = fin_quarter_price_durations
        ret_index = pd.DatetimeIndex.strftime(df.index, "%Y-%m-%d")
        reg_exp   = r'qo\S+'
    
    #print("%r: %r" %(df.iloc[0]['Symbol'], fig))

    if items is None:
        items = df.iloc[1:].index

    # Create new fields
    cols = list(df.columns)
    # Populate the list of columns the percentage changes are already computed.
    # This list can be used to avoid recalculation of the same columns.
    computed_list = []
    for c in cols:
        if c in computed_list:
            continue
        if c == 'Date':
            continue
        if c == 'Symbol':
            continue
        #print("%r: Column: %r, fig: %r" %(df.iloc[0]['Symbol'], c, fig))

        for i in range(len(durations)):
            match = re.search(reg_exp, c)
            if match is not None:
                c = c[0:match.span()[0]-1]

            key = '{} {}'.format(c,fields[i])
            #key = key.replace('- ','').replace(' ', '_').replace('-','')

            if key in computed_list:
                # The execution path may not reach till this point.
                # It should be skipped by if c in computed_list: continue
                continue
            computed_list.append(key)
            #print("Key: %r" %(key))
            if key not in list(df.keys()):
                df[key]=nan
            duration = durations[i]
            #for index, d in df.iloc[1:].iterrows():
            #    df = fin_percent_change_row(key, index, c, d, df, duration)
            for index in items:
                df = fin_percent_change_row(key, index, c, df.loc[index], df, duration)

        # Whole Change Case
        match = re.search(reg_exp, c)
        if match is not None:
            c = c[0:match.span()[0]-1]
        if c == 'Date':
            continue
        if c == 'Symbol':
            continue
 
        key = '{} {}'.format(c,fields[-1])
        #key = key.replace('- ','').replace(' ', '_').replace('-','')
        if key in computed_list:
            continue
        computed_list.append(key)
        #print("Key: %r" %(key))
        if key not in list(df.keys()):
            df[key]=nan
        #for index, d in df.iloc[1:].iterrows():
        #    df = fin_percent_change_row(key, index, c, d, df)
        for index in items:
            df = fin_percent_change_row(key, index, c, df.loc[index], df)

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

def update_US_fin_stmt_percent_change(mysql_engine, stk, fig, stmt_type, table):
    df = pd.DataFrame()
    df = form_df(stk[fig]['financial-statements'][stmt_type], stmt_type)
   
    # Delete empty columns in balance-sheet
    if stmt_type == 'balance-sheet':
        if 'Current Assets' in list(df.columns):
            del df['Current Assets']
        if 'Current Liabilities' in list(df.columns):
            del df['Current Liabilities']
        if 'Non-Current Assets' in list(df.columns):
            del df['Non-Current Assets']
        if 'Non-Current Liabilities' in list(df.columns):
            del df['Non-Current Liabilities']

    df['Symbol'] = stk['bscs']['symbol']
    df['Date'] = pd.DatetimeIndex.strftime(df.index, "%Y-%m-%d")
    cols = list(df.columns)
    cols = cols[-2:]+cols[:-2]
    df = df[cols]
    #df.index = pd.to_datetime(df['Date'])
    # Let the columns have spaces or special chars
    #new_cols = {}
    #for c in cols:
    #    new_cols[c] = c.replace('- ','').replace(' ', '_').replace('-','')
    #df.rename(columns=new_cols, inplace=True)
    items = df.index
    if len(items) == 0:
        return
   
    if mysql_exists_table(mysql_engine, table):
        query = 'select * from '+table+' where Symbol = \'{}\''.format(stk['bscs']['symbol'])
        edf = read_from_sql(query, mysql_engine)
        if not edf.empty:
            ret = same_calculations(copy.deepcopy(edf), fig)
            if ret:
                #Only once due to wrong entries
                print("Deleting {} entries from {}".format(stk['bscs']['symbol'], table))
                mysql_engine.execute("delete from {} where Symbol='{}';".format(table, stk['bscs']['symbol']))
                edf = pd.DataFrame()

        # Exclude already existing entries in the database.
        # Calculate percentage change for the new entries only.
        df  = df[~df.index.isin(edf.index)]
        # Calculate percentage change only for the below items
        items = df.index
        # Up-to-date. Return
        if len(items) == 0:
            return
        #print("Total entries to calculate: %r" %(items))
        df = edf.append(df, sort=True)
   
    print("****** {} *******".format(table))
    df = fin_change(df, fig, items=items)
    # Replace NaN with None
    df = df.where(pd.notnull(df), None)
    if fig=='fig':
        items = pd.DatetimeIndex.strftime(items, "%Y-%m")
    else:
        items = pd.DatetimeIndex.strftime(items, "%Y-%m-%d")
    #print(df.loc[items])

    #Only once due to wrong entries
    #mysql_engine.execute("delete from {} where Symbol='{}';".format(table, stk['bscs']['symbol']))

    mysql_update_table(mysql_engine, table, df.loc[items], check=True, insert=True, unknown_table=True, cols_type='fin', temp=True, date_column=False, format_columns=False)

# By error, calculated same values for all yoys and qoqs
# Check if two columns have the same values
def same_calculations(df, fig):
    df.dropna(axis=1,inplace=True)
    if df.empty:
        return False

    columns = list(df.columns)
    if fig == 'fig':
        r1 = 'yoy'
        r2 = 'yo3y'
    else:
        r1 = 'qoq'
        r2 = 'qo2q'

    f1 = f2 = None
    for c in columns:
        if c.find(r1) != -1:
            f1 = c
        if c.find(r2) != -1:
            f2 = c
        if f1 and f2:
            break

    if f1 is None:
        return False

    ret = df[f1].equals(df[f2])
    if ret:
        print(df[[f1,f2]])
    return ret

def update_US_fin_percent_change(mysql_engine, mysql_fin_change_engine, stk, fig):
    if fig == 'fig':
        income_table = 'income_table'
        balance_table = 'balance_table'
        cash_table = 'cash_table'
    else:
        income_table = 'income_quart_table'
        balance_table = 'balance_quart_table'
        cash_table = 'cash_quart_table'

    if fig not in stk.keys():
        print("No financial figures available. Exiting percent calculation")
        return
    if 'financial-statements' not in stk[fig].keys():
        print("No financial figures available. Exiting percent calculation")
        return

    if 'income-statement' in stk[fig]['financial-statements'].keys():
        update_US_fin_stmt_percent_change(mysql_engine, stk, fig, 'income-statement', income_table)
    if 'cash-flow' in stk[fig]['financial-statements'].keys():
        update_US_fin_stmt_percent_change(mysql_engine, stk, fig, 'cash-flow', cash_table)
    if 'balance-sheet' in stk[fig]['financial-statements'].keys():
        update_US_fin_stmt_percent_change(mysql_engine, stk, fig, 'balance-sheet', balance_table)

def US_fin_percent_change(mysql_engine, db, stk, sem=None):
    t = time.time()
    #print("sem acquire: %r: %r: %r" %(threading.current_thread().name, stk['bscs']['symbol'], stk['bscs']['name']))
    if 'fin_percent_update_date' in stk['bscs'].keys():
        if dt.now().date() - stk['bscs']['fin_percent_update_date'].date() < timedelta(30):
        #if False:
            if sem:
                #print("%s sec: sem release: %r: %r: %r" %(time.time()-t, threading.current_thread().name, stk['bscs']['symbol'], stk['bscs']['name']))
                sem.release()
            return
    update_US_fin_percent_change(mysql_engine, stk, 'fig')
    update_US_fin_percent_change(mysql_engine, stk, 'quart_fig')
    db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.fin_percent_update_date": dt.now()}})
    if sem:
        #print("%s sec: sem release: %r: %r: %r" %(time.time()-t, threading.current_thread().name, stk['bscs']['symbol'], stk['bscs']['name']))
        sem.release()

def US_fin_percent_per_process(stk, sem, core):
    # Set process affinity
    aff = 0 | 1 << core
    os.system("taskset -p %r %d >/dev/null 2>&1" %(str(hex(aff)), os.getpid()))

    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')
    mysql_fin_change_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin_Change')
    US_fin_percent_change(mysql_engine, mysql_fin_change_engine, db, stk)

    close_db_client(c)
    close_sql_connection(mysql_engine)
    sem.release()

# Calculate percentage change of the annual/quarter fundamental params
# like sales, profits, cash flows, tangible/total book value etc
def update_all_US_fin_percent_change():
    #os.system("taskset -p 0xfffff %d > /dev/null 2>&1" % os.getpid())
    sem = multiprocessing.BoundedSemaphore(num_cores)
    #sem = threading.BoundedSemaphore(num_cores)
    c  = open_db_client()
    db = c['Stocks']
    mysql_engine = open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')

    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(2).sort([["sno",1]])
    print(stocks.count())

    for i, stk in enumerate(stocks):
        #if i > 8:
        #    break
        sem.acquire()
        print("%d: %r: %r" %(i, stk['bscs']['symbol'], stk['bscs']['name']))
        #US_fin_percent_change(mysql_engine, db, stk, sem)
        #US_fin_percent_per_process(stk, sem)
        multiprocessing.Process(target=US_fin_percent_per_process, args=(stk, sem, i%num_cores,)).start()

    time.sleep(30)
    close_db_client(c)
    close_sql_connection(mysql_engine)

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
    c  = open_db_client()
    db = c['Stocks']
    count=0

    stocks = db.US_Stocks.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    print(stocks.count())

    for i, stk in enumerate(stocks):
        print("%d: %r: %r" %(i, stk['bscs']['symbol'], stk['bscs']['name']))
        miss_count = update_US_fin_stmt_errors(db.US_Stocks, copy.deepcopy(stk))
        count=count+miss_count

    print("Miss Count: %r" %(count))
    close_db_client(c)

