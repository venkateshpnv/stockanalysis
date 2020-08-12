import sys
import os
import time
#Web Driver
import selenium
from selenium import webdriver
from seleniumwire import webdriver as wire_webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains as ac
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import multiprocessing
import threading
import urllib3
import OpenSSL

from io import StringIO

import gc

import pymysql

# Parsing HTML
import requests 

import copy

from math import isnan, nan

#Yahoo Financials
from yahoofinancials import YahooFinancials as yf

import pandas_datareader as pdr
import pandas_datareader.data as data
import pandas as pd

import timestring

# Excel operations
#import csv
import xlrd
import xlwt

# Date
import datetime
from datetime import datetime as dt, timedelta
from dateutil.relativedelta import relativedelta
from datetime import date

#List Files
from fractions import Fraction

import smtplib
import re

from bs4 import BeautifulSoup

import pprint

import excel
import conf
from datastructures import *
import parse_html
import DB
from common import *
import hdf5


def open_browser(head=None, wiredriver=False):
    profile = webdriver.FirefoxProfile()
    capabilities = DesiredCapabilities.FIREFOX

    options = Options()
    #if head == 'headless':
    #    options.add_argument('--headless')

    profile.set_preference("browser.cache.disk.enable", False)
    profile.set_preference("browser.cache.memory.enable", False)
    profile.set_preference("browser.cache.offline.enable", False)
    profile.set_preference("network.http.use-cache", False)
    profile.set_preference("browser.privatebrowsing.autostart", True)
    profile.set_preference("dom.webnotifications.enabled", False)
    profile.add_extension(extension='/home/vpetla/.mozilla/firefox/ekwma54v.default-release/extensions/jid1-P34HaABBBpOerQ@jetpack.xpi')
    profile.add_extension(extension='/home/vpetla/.mozilla/firefox/ekwma54v.default-release/extensions/{246C9D65-51E6-4B0C-9CCF-B081B7BF9242}.xpi')
    if wiredriver:
        browser = wire_webdriver.Firefox(profile, options=options, capabilities=capabilities)
    else:
        browser = webdriver.Firefox(profile, options=options, capabilities=capabilities)
    #browser.set_page_load_timeout(30)
    #browser.maximize_window()
    return browser

def close_browser(br):
    #br.close()
    br.delete_all_cookies()
    br.quit()

def send_email(message):
    # creates SMTP session 
    s = smtplib.SMTP('smtp.gmail.com', 587) 
      
    # start TLS for security
    s.ehlo()
    s.starttls() 
      
    # Authentication 
    s.login("askpvenkatesh@gmail.com", "tasche#gm") 
      
    # message to be sent 
    message = "Hello World."
      
    # sending the mail 
    s.sendmail("askpvenkatesh@gmail.com", "askpvenkatesh@gmail.com", message) 
      
    # terminating the session 
    s.quit() 

def send_email2(user, pwd, recipient, subject, body):

    FROM = user
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = subject
    TEXT = body

    # Prepare actual message
    #message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    #""" % (FROM, ", ".join(TO), SUBJECT, TEXT)

    message = MIMEMultipart('alternative')
    message['Subject'] = subject
    message['From'] = user
    message['To'] = recipient
    message.attach(MIMEText(body, 'html'))

    #server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server = smtplib.SMTP("smtp.gmail.com", 587)
    #server.set_debuglevel(1)
    server.ehlo()
    server.starttls()
    server.login(user, pwd)
    server.sendmail(FROM, TO, message.as_string())
    #server.sendmail(FROM, TO, message)
    server.close()
    print('successfully sent the mail')

def index_change(country, sym, name, num_days, data_type):
    change = 0
    symbol = sym.replace('.', '-')
    if data_type == 'HOT':
        end = dt.now()
        diff = end.weekday() - 4
        #If weekend
        if diff > 0:
            end = end - timedelta(days=diff+1)
        start = end - timedelta(days=num_days)
        diff = start.weekday() - 4
        if diff > 0:
            start = start - timedelta(days=diff+1)
        try:
            #print("Symbol: %s, Name: %s" %(sym, name))
            #read = pdr.DataReader(symbol, 'morningstar', start, end)
            read = pdr.DataReader(symbol, 'yahoo', start, end)
        except pdr._utils.RemoteDataError:
            PRINT_ERR("Unable to get data for %s"%(sym))
            return None
        except KeyError:
            PRINT_ERR("Unable to get data for %s"%(sym))
            return None
 
        en_price = read.iat[-1, read.columns.get_loc('Adj Close')]
        st_price = read.iat[0, read.columns.get_loc('Adj Close')]
        change = en_price/st_price - 1
    return change, round((en_price-st_price), 2)

# Deprecated. Use hdf_price_change().
def price_change(country, sym, name, num_days, data_type):
    change,diff=index_change(country,sym,name,num_days,data_type)
    return change

def check_price_change(country, sym, stock, name, change, req_change, count, sheet, sheet_type, excel_type):
    if change >= req_change:
        #print("sym: %s, name: %s, change: %d percent" %(sym, name, change*100))
        count += 1
        if excel_type == 'EXCEL':
            excel.write_to_price_change_excel(count, sheet, stock, sheet_type)

    elif change < -(req_change):
        #print("sym: %s, name: %s, change: -%d percent" %(sym, name, change*100))
        count += 1 
        if excel_type == 'EXCEL':
            excel.write_to_price_change_excel(count, sheet, stock, sheet_type)

    return count


def price_suprise(country, collection, stock, sym, name, change_percent, xl, criteria, db_type, excel_type):
   #st_price = read.iat[0, read.columns.get_loc('Close')]
    #en_price = read.iat[-1, read.columns.get_loc('Close')]
   
    if criteria == ALL or criteria & YEAR:
        change = hdf5.hdf_price_change(country, sym, 365)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.year", change)
            if excel_type == 'EXCEL':
                sheet = xl.get_sheet(0)
            else:
                sheet = None
            conf.PR_YR_COUNT = check_price_change(country, sym, stock, name, change, 0.40, conf.PR_YR_COUNT, sheet, 'YEAR', excel_type)
    
    if criteria == ALL or criteria & QUARTER:
        change = hdf5.hdf_price_change(country, sym, 90)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.quarter", change)
            if excel_type == 'EXCEL':
                sheet = xl.get_sheet(1)
            else:
                sheet = None
            conf.PR_QR_COUNT = check_price_change(country, sym, stock, name, change, 0.30, conf.PR_QR_COUNT, sheet, 'QUARTER', excel_type)
    
    if criteria == ALL or criteria & MONTH:
        change = hdf5.hdf_price_change(country, sym, 30)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.month", change)
            if excel_type == 'EXCEL':
                sheet = xl.get_sheet(2)
            else:
                sheet = None
            conf.PR_MON_COUNT = check_price_change(country, sym, stock, name, change, 0.20, conf.PR_MON_COUNT, sheet, 'MONTH', excel_type)
    
    if criteria == ALL or criteria & WEEK:
        change = hdf5.hdf_price_change(country, sym, 7)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.week", change)
            if excel_type == 'EXCEL':
                sheet = xl.get_sheet(3)
            else:
                sheet = None
            conf.PR_WEEK_COUNT = check_price_change(country, sym, stock, name, change, 0.10, conf.PR_WEEK_COUNT, sheet, 'WEEK', excel_type)

    if criteria == ALL or criteria & DAY:
        change = hdf5.hdf_price_change(country, sym, 1)
        if change:
            if db_type == 'SYNC_DB':
                DB.update_field(collection, sym, "price_change.day", change)
            if excel_type == 'EXCEL':
                sheet = xl.get_sheet(4)
            else:
                sheet = None
            conf.PR_DAY_COUNT = check_price_change(country, sym, stock, name, change, 0.10, conf.PR_DAY_COUNT, sheet, 'DAY', excel_type)

    DB.update_field(collection, sym, "price_change.date", str(dt.now()))

def get_change(df, field):
    if df.iloc[0][field] and not isnan(df.iloc[0][field]):
        return df.iloc[0][field]
    else:
        return df.iloc[1][field]

# Fix mess caused by update_price_change() caused by the query
# query = 'select `Date`, `Adj Close` from %s where `Day Change` is NULL order by Date'
def nullify_price_change_error_stk(country, collection, sym, sql_engine):
    table_name = DB.get_symbol_table_name(sym)
    if DB.mysql_exists_table(sql_engine, table_name):
        query = 'select `Date`, `Adj Close` from %s where `Day Change` = `Whole Change`' %(table_name)
        df = DB.read_from_sql(query, sql_engine)
        if not df.empty:
            for index, d in df.iterrows():
                end_date = str(pd.to_datetime(index).date())
                query = 'select Date, `Adj Close`, `Day Change` from {} where Date = \'{}\''.format(table_name, end_date)
                cur_df = DB.read_from_sql(query, sql_engine)
                query = 'select Date, `Adj Close` from {} where `Date` < \'{}\' order by Date desc limit 1'.format(table_name, end_date)
                prev_df = DB.read_from_sql(query, sql_engine)
                price_change = round(cur_df['Adj Close'][-1]/prev_df['Adj Close'][-1] - 1, len(str(cur_df['Day Change'][-1]).split('.')[1]))
                if abs(abs(price_change) - abs(cur_df['Day Change'][-1])) > 0.05: # Atleast 5% difference
                    # Nullify from here to end of the table
                    #query = 'select * from {} where `Date` BETWEEN \'{}\' and  NOW()'.format(table_name, end_date)
                    query = 'select `Date`, {} from {} where `Date` BETWEEN \'{}\' and  NOW()'.format(', '.join(['`{}`'.format(c) for c in price_change_fields]), table_name, end_date)
                    df2 = DB.read_from_sql(query, sql_engine)
                    for field in price_change_fields:
                        df2[field] = None
                    print("Updating change: %r" %(cur_df))
                    DB.mysql_update_table(sql_engine, table_name, df2, check=True)
                    break

 
def nullify_price_change_errors():
    country = 'US'
    c = DB.open_db_client()
    db = c['Stocks']
    collection = DB.get_collection(country, db)
    sql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

    #stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
    symbols = DB.get_symbols_from_sql(country, sql_engine)

    try:
        for i, symbol in enumerate(symbols):
            print("%d: %r" %(i, symbol))
            nullify_price_change_error_stk(country, collection, symbol, sql_engine)
    finally:
        DB.close_sql_connection(sql_engine)
        DB.close_db_client(c)

def update_price_change(country, collection, sym, sem, sql_engine):
    #st_price = read.iat[0, read.columns.get_loc('Close')]
    #en_price = read.iat[-1, read.columns.get_loc('Close')]
    table_name = DB.get_symbol_table_name(sym)
    change = 0

    wdf = pd.DataFrame(columns=['Date']+price_change_fields) 

    try:
        if DB.mysql_exists_table(sql_engine, table_name):
            #query = 'select `Date`, `Adj Close` from %s order by Date' %(table_name)
            query = 'select `Date`, `Adj Close` from %s where `Day Change` is NULL order by Date' %(table_name)
            #query = 'select `Date`, `Adj Close`, {} from {}'.format(', '.join(['`{}`'.format(c) for c in price_change_fields]), table_name)
            df = DB.read_from_sql(query, sql_engine)
            if df.empty:
                return

            ipo_price = df['Adj Close'][0]

            for index, d in df.iloc[1:].iterrows():
                cur_price = d['Adj Close']
                cur_date = pd.to_datetime(index).date()
                cur_date_str = str(cur_date)
                wdf.loc[cur_date_str]=nan
                wdf.loc[cur_date_str]['Date'] = cur_date_str
                #Percent Changes for Day, Week, Month etc
                for i in range(len(price_change_durations)):
                    start_price = DB.mysql_get_price(sql_engine, table_name, str(cur_date - price_change_durations[i]), str(cur_date))
                    change = percent_change(start_price, cur_price)
                    wdf.loc[cur_date_str][price_change_fields[i]] = change

                # Whole Change
                change = percent_change(ipo_price, cur_price)
                wdf.loc[cur_date_str][price_change_fields[-1]] = change
                #wdf.drop(wdf.index, inplace=True)

            print("mysql: percent_change: %s"%(sym))
            DB.mysql_update_table(sql_engine, table_name, wdf)

            query = 'select `Date`, {} from {} order by Date desc limit 2'.format(', '.join(['`{}`'.format(c) for c in price_change_fields]), table_name)
            df = DB.read_from_sql(query, sql_engine)

            change = get_change(df, 'Day Change')
            DB.update_field(collection, sym, "price_change.day", change)

            change = get_change(df, 'Week Change')
            DB.update_field(collection, sym, "price_change.week", change)

            change = get_change(df, 'Month Change')
            DB.update_field(collection, sym, "price_change.month", change)

            change = get_change(df, 'Quarter Change')
            DB.update_field(collection, sym, "price_change.quarter", change)

            change = get_change(df, 'Half Year Change')
            DB.update_field(collection, sym, "price_change.half_year", change)

            change = get_change(df, 'Year Change')
            DB.update_field(collection, sym, "price_change.year", change)

            change = get_change(df, 'Five Year Change')
            DB.update_field(collection, sym, "price_change.five_year", change)

            change = get_change(df, 'Ten Year Change')
            DB.update_field(collection, sym, "price_change.ten_year", change)

            change = get_change(df, 'Whole Change')
            DB.update_field(collection, sym, "price_change.whole", change)

            end_date = str(dt.now().date())
            #get 52 week high
            #select max(`Adj Close`) from STKSP500 where Date between date_sub('2020-03-20', INTERVAL 1 YEAR) and '2020-03-20';
            query ='select max(`Adj Close`) from {} where Date between date_sub(\'{}\', INTERVAL 1 YEAR) and \'{}\''.format(table_name, end_date, end_date)
            result=sql_engine.execute(query)
            high_price = result.first()[0]
            #high_price = hdf5.hdf_get_high_n_days(df, 365)
            DB.update_field(collection, sym, "bscs.fiftytwoweek_high", high_price)
            #get 52 week low
            query ='select min(`Adj Close`) from {} where Date between date_sub(\'{}\', INTERVAL 1 YEAR) and \'{}\''.format(table_name, end_date, end_date)
            #query ='select min(`Adj Close`) from ' + table_name + ' where Date between Date between date_sub(%s, INTERVAL 1 YEAR);'%(end_date, end_date)
            result=sql_engine.execute(query)
            low_price = result.first()[0]
            #low_price = hdf5.hdf_get_low_n_days(df, 365)
            DB.update_field(collection, sym, "bscs.fiftytwoweek_low", low_price)

            # Get today's price
            query = 'select `Adj Close` from {} order by Date desc limit 1'.format(table_name)
            result=sql_engine.execute(query)
            price = result.first()[0]
            #price = hdf5.hdf_get_price(sym, df, dt.now().date())
            
            if high_price == 0:
                change = 0
            else:
                change = (price/high_price) - 1

            DB.update_field(collection, sym, "price_change.with_52week_high", change)
            
            if low_price == 0:
                change = 0
            else:
                change = (price/low_price) - 1

            DB.update_field(collection, sym, "price_change.with_52week_low", change)
        else:
            change=None
            DB.update_field(collection, sym, "price_change.day", change)
            DB.update_field(collection, sym, "price_change.week", change)
            DB.update_field(collection, sym, "price_change.month", change)
            DB.update_field(collection, sym, "price_change.quarter", change)
            DB.update_field(collection, sym, "price_change.half_year", change)
            DB.update_field(collection, sym, "price_change.year", change)
            DB.update_field(collection, sym, "price_change.whole", change)
            DB.update_field(collection, sym, "bscs.fiftytwoweek_high", change)
            DB.update_field(collection, sym, "bscs.fiftytwoweek_low", change)
            DB.update_field(collection, sym, "price_change.with_52week_high", change)
            DB.update_field(collection, sym, "price_change.with_52week_low", change)
 
    finally:
        DB.update_field(collection, sym, "price_change.date", dt.now())
        if sem:
            sem.release()

def fork_hdf5_process(country, sem):
    ## Randomly get all records whose price is not updated till today
    ##pipeline = [{'$sample': {'size':num_docs}},
    ##            {'$match' : {"price_change.date": {'$ne':today}}},
    ##            #{"$group": {"_id": _id, "count": {"$sum":1}}},
    ##            #{"$group": {"_id": None, "total": {"$sum": 1}, "details":{"$push":{"groupby": "$_id", "count": "$count"}}}}
    ##            ]

    ##stocks = db.US_Stocks.aggregate(pipeline, allowDiskUse=True).batch_size(10)
    c = DB.open_db_client()
    db = c['Stocks']
    collection = DB.get_collection(country, db)
    sql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')

    today=str(dt.now().date())
    num_docs = collection.find({}).count()
    #num_docs = collection.find({"bscs.price_date": {'$ne':today}})
    if num_docs == 0:
        close_db_client(c)
        close_sql_connection(sql_engine)
        return

    symbols = DB.get_symbols_from_sql(country, sql_engine)
    #symbols = get_symbols_from_mongo(collection)
    
    if country == 'India':
        indices = India_indices
    else:
        indices = US_indices 
    stk = {}
    stk['bscs']={}

    try:
        ##Indices
        for k in indices.keys():
            stk['bscs']['symbol'] = k
            stk['bscs']['name'] = indices[k]
            sem.acquire()
            #update_price_change(country, collection, stk['bscs']['symbol'], sem, sql_engine)
            threading.Thread(target=update_price_change, args=(country, collection, copy.deepcopy(stk['bscs']['symbol']), sem, sql_engine,)).start()

        ## Randomly get all records whose price is not updated till today
        ##pipeline = [{'$sample': {'size':num_docs}},
        ##            {'$match' : {"bscs.price_date": {'$ne':today}}},
        ##            #{"$group": {"_id": _id, "count": {"$sum":1}}},
        ##            #{"$group": {"_id": None, "total": {"$sum": 1}, "details":{"$push":{"groupby": "$_id", "count": "$count"}}}}
        ##            ]

        ##stocks = db.US_Stocks.aggregate(pipeline, allowDiskUse=True).batch_size(10)
        ##stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
 
        i=0
        today=dt.now().date()
        for i, stk in enumerate(stocks):
            #if ignore_stock(stk):
            #    continue
            #print("%r" %(i))

            #last_updated_date = dt.strptime(stk['price_change']['date'].split(' ')[0], "%Y-%m-%d").date()
            #if last_updated_date >= today:
            #    continue
            #if stk['bscs']['symbol'] not in symbols:
            #    continue
            if 'price_failcount' in stk['bscs'].keys() and stk['bscs']['price_failcount'] > 5:
                continue
 
            sem.acquire()
            #update_price_change(country, collection, stk['bscs']['symbol'], sem, sql_engine)
            t = threading.Thread(target=update_price_change, args=(country, collection, copy.deepcopy(stk['bscs']['symbol']), sem, sql_engine,))
            t.start()
            #if i > 10:
            #    break;

    finally:
        # Wait till all threads are completed. You can use join() instead.
        # But need to track threads and update variables.
        # Simplest way is to wait for tentative time taken for the end threads to complete
        # Randomly estimated it to be 10 sec and it perfectly works.
        time.sleep(30)
        #if t:
        #    t.join()
        DB.close_sql_connection(sql_engine)
        DB.close_db_client(c)
    print("MYSQL Stocks tried :%r"%(i))


def fork_betas_process(country, sem):
    c = DB.open_db_client()
    db = c['Stocks']
    collection = DB.get_collection(country, db)
    num_docs = collection.find({}).count()
    # Randomly get all records whose price is not updated till today
    #pipeline = [{'$sample': {'size':num_docs}},
    #            {'$match' : {"price_change.date": {'$ne':today}}},
    #            #{"$group": {"_id": _id, "count": {"$sum":1}}},
    #            #{"$group": {"_id": None, "total": {"$sum": 1}, "details":{"$push":{"groupby": "$_id", "count": "$count"}}}}
    #            ]

    #stocks = db.US_Stocks.aggregate(pipeline, allowDiskUse=True).batch_size(10)
    stocks = collection.find({},no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
 
    today=str(dt.now().date())
    i=0
    for stk in stocks:
        if DB.ignore_stock(stk):
            continue

        print("Betas: %d: %s: %s"%(i,stk['bscs']['symbol'],stk['bscs']['name']))
        sem.acquire()
        #DB.update_stock_betas(country, collection, stk)
        threading.Thread(target=DB.update_stock_betas, args=(country, collection, stk, sem,)).start()
        #break
        i = i + 1
        #if i > 10:
        #    break

    # Wait randomly till all threads are completed
    time.sleep(10)
    DB.close_db_client(c)
    print("Total stocks: %r" %(i))


# Update the DB with yearly, quarterly and monthly percentage price change
def update_all_stocks_price_change(country):
    i = 0
    max_threads = multiprocessing.cpu_count() * DB.thread_factor
    hdf5_sem = threading.BoundedSemaphore(max_threads)
    #betas_sem = threading.BoundedSemaphore(max_threads)
 
    print("Updating price percent changes")
    fork_hdf5_process(country, hdf5_sem)
    #fork_betas_process(country, betas_sem)
    #hdf5_process = multiprocessing.Process(target=fork_hdf5_process, args=(country, hdf5_sem, ))
    #betas_process = multiprocessing.Process(target=fork_betas_process, args=(country, betas_sem, ))
    
    #hdf5_process.start()
    #betas_process.start()

    #hdf5_process.join()
    #betas_process.join()

def pcent(val):
    return str(round(val *100, 2))+'%'

# direction : -1 -> ascending order. Used for negative percent change
# direction : 1 -> descending order. Used for positive percent change.
def get_stocks(country, low_mcap, high_mcap, direction, change, duration):

    # duration can be "day", "week", "month", "quarter", "half_year", "year"
    price_change="price_change.%s"%(duration)
    # get all stocks with percentage greater than change in descending order
    if direction == -1:
        cond = '$lte'
    # get all stocks with percentage less than change in ascending order
    else:
        cond = '$gte'

    factor = 1
    if country == 'US':
        mcap = "MCap in Millions"
        #Convert to billions for mcap greater than 1 billion.
        if high_mcap > 1000:
            factor = 1/1000
            mcap = "Mcap Bn"
    elif country == 'India':
        mcap = "MCap in Crores"

    db = DB.open_db('Stocks')
    collection = DB.get_collection(country, db)
    
    entries = []
    if country == 'US':
        head=["Symbol", "Name", "Since", "Sectr", mcap, "Vol", "Price", "6M Beta", "52Wk Hgh", "52Wk Lw", "Day Chg", "Wk Chg", "Mth Chg", "Qrtr Chg", "Hf Yr Chg", "Yr Chg", "With 52Wk Hgh", "With 52Wk Lw"]
    else:
        head=["Symbol", "Name", "Since", "Sectr", mcap, "Vol", "Price", "6M Beta", "52Wk Hgh", "52Wk Lw", "Day Chg", "Wk Chg", "Mth Chg", "Qrtr Chg", "Hf Yr Chg", "Yr Chg", "With 52Wk Hgh", "With 52Wk Lw"]

    entries.append(head)
    stocks = collection.find({'$and': [{'bscs.mcap':{'$gte':low_mcap, '$lt':high_mcap}}, {price_change:{cond:change}}]}).sort([[price_change,-direction]])
    #query = {'$and': [{'bscs.mcap':{'$gte':low_mcap, '$lt':high_mcap}}, {price_change:{cond:change}}]}
    #stocks = db.US_Stocks.find(query).sort([[price_change,direction]])
    for stk in stocks:
        #if DB.ignore_stock(stk):
        #    continue

        bscs  = stk['bscs']
        pchg = stk['price_change']
        print("%r: %s: %s" %(stk['sno'], bscs['symbol'], bscs['name']))
        entry = [ ]
        entry.append(bscs['symbol'])
        entry.append(bscs['name'])
        if country == 'US':
            entry.append(str(bscs['since']))
        else:
            entry.append(str("-"))
        entry.append(str(bscs['sector']))
        entry.append(str(round(bscs['mcap']*factor, 2)))
        if 'volume' in bscs.keys():
            entry.append(str(round(bscs['volume']/1000, 2))+'k')
        else:
            entry.append("-")
        entry.append(str(bscs['price']))
        #try:
        if stk['fig']['betas']['six_months'] != None:
            entry.append(str(round(stk['fig']['betas']['six_months']['beta'], 2)))
        else:
            entry.append("-")
        #entry.append(str(round(stk['fig']['betas']['six_months']['beta'], 2)))
        #except Exception as e:
        #    collection.update({'bscs.symbol': bscs['symbol']}, {'$set': {"fig.betas.six_months.beta": 0}})
        #    entry.append(str("None"))
        if 'fiftytwoweek_high' in bscs.keys():
            entry.append(str(round(bscs['fiftytwoweek_high'], 2)))
        else:
            entry.append("")
        if 'fiftytwoweek_low' in bscs.keys():
            entry.append(str(round(bscs['fiftytwoweek_low'], 2)))
        else:
            entry.append("")
        entry.append(pcent(pchg['day']))
        entry.append(pcent(pchg['week']))
        entry.append(pcent(pchg['month']))
        entry.append(pcent(pchg['quarter']))
        entry.append(pcent(pchg['half_year']))
        entry.append(pcent(pchg['year']))
        if 'with_52week_high' in pchg.keys():
            entry.append(pcent(pchg['with_52week_high']))
        else:
            entry.append("")
        if 'with_52week_low' in pchg.keys():
            entry.append(pcent(pchg['with_52week_low']))
        else:
            entry.append("")
        
        entries.append(entry)

    DB.close_db()
    return entries

def build_html_price_change(s, country, low_mcap, high_mcap, direction, change, duration, segment): 
    e = get_stocks(country, low_mcap, high_mcap, direction, change, duration)
    s = parse_html.html_text(s, segment)
    if len(e) > 1:
        #entries = [["Up"]]
        entries = e
        s = parse_html.html_set_line(s)
        s = parse_html.html_text(s, ["Up"])
        s = parse_html.html_set_line(s)
        s = parse_html.html_text(s, entries, highlight_columns[duration])
        s = parse_html.html_set_line(s)
    e = get_stocks(country, low_mcap, high_mcap, -direction, -change, duration)
    if len(e) > 1:
        #entries = [["Down"]]
        entries = e
        s = parse_html.html_text(s, ["Down"])
        s = parse_html.html_set_line(s)
        s = parse_html.html_text(s, entries, highlight_columns[duration])
        s = parse_html.html_set_line(s)
    return s

#Minimum percent changes per day, week, month etc that should
# be considered for stocks with different ranges of mcaps
# in descending order
# [> 100bn, 10bn to 100bn, 5bn to 10bn, 1bn to 5bn, 1mn to 1bn]
pcent_chg = {}
pcent_chg['day']       = [0.03, 0.05, 0.05, 0.10, 0.15]
pcent_chg['week']      = [0.05, 0.05, 0.10, 0.15, 0.20]
pcent_chg['month']     = [0.05, 0.05, 0.10, 0.15, 0.20]
pcent_chg['quarter']   = [0.10, 0.10, 0.20, 0.25, 0.25]
pcent_chg['half_year'] = [0.15, 0.15, 0.25, 0.30, 0.50]
pcent_chg['year']      = [0.20, 0.20, 0.25, 0.30, 0.50]

# Day change column position.
# Week = Day + 1
# Month = Week + 1 etc
day_col = 10
week_col = day_col + 1
month_col = week_col + 1
quarter_col = month_col + 1
half_year_col = quarter_col + 1
year_col = half_year_col + 1

highlight_columns = { 'day': day_col, 'week':week_col, 'month':month_col, 'quarter':quarter_col, 'half_year':half_year_col, 'year':year_col }

def get_price_changes(s, country, duration):

    if country == 'US':
        Bn = 1000
        Tn = 1000*Bn
        #s = parse_html.html_set_line(s)
        s = build_html_price_change(s, 'US', 100*Bn, 10*Tn, 1, pcent_chg[duration][0], duration, ["MCap 100 Bn and above"])
        s = build_html_price_change(s, 'US', 10*Bn, 100*Bn,   1, pcent_chg[duration][1], duration, ["MCap 10 Bn and 100 Bn"])
        s = build_html_price_change(s, 'US', 5*Bn, 10*Bn,     1, pcent_chg[duration][2], duration, ["MCap 5 Bn and 10 Bn"])
        s = build_html_price_change(s, 'US', 1*Bn, 5*Bn,      1, pcent_chg[duration][3], duration, ["MCap 1 Bn and 5 Bn"])
        s = build_html_price_change(s, 'US', 1, 1*Bn,         1, pcent_chg[duration][4], duration, ["MCap < 1 Bn"])
    elif country == 'India':
        Bn = 100 # crores
        Tn = 100 * Bn
        #s = parse_html.html_set_line(s)
        s = build_html_price_change(s, 'India', 100*Bn, 10*Tn, 1, pcent_chg[duration][0], duration, ["MCap 10k Cr and above"])
        s = build_html_price_change(s, 'India', 10*Bn, 100*Bn,   1, pcent_chg[duration][1], duration, ["MCap 1k Cr and 10k Cr"])
        s = build_html_price_change(s, 'India', 5*Bn, 10*Bn,     1, pcent_chg[duration][2], duration, ["MCap 500 Cr and 1k Cr"])
        s = build_html_price_change(s, 'India', 1*Bn, 5*Bn,      1, pcent_chg[duration][3], duration, ["MCap 100 Cr and 500 Cr"])
        s = build_html_price_change(s, 'India', 1, 1*Bn,         1, pcent_chg[duration][4], duration, ["MCap < 100 Cr"])
    return s

def send_email_price_changes(country):
    s = parse_html.html_head()
    s = parse_html.html_text(s, ["Daily Price Surprises"])
    s = parse_html.html_set_line(s)
    s = get_price_changes(s, country, 'day')
    s = parse_html.html_text(s, ["Weekly Price Surprises"])
    s = parse_html.html_set_line(s)
    s = get_price_changes(s, country, 'week')
    s = parse_html.html_text(s, ["Monthly Price Surprises"])
    s = parse_html.html_set_line(s)
    s = get_price_changes(s, country, 'month')
    s = parse_html.html_text(s, ["Quarterly Price Surprises"])
    s = parse_html.html_set_line(s)
    s = get_price_changes(s, country, 'quarter')
    s = parse_html.html_text(s, ["Half Yearly Price Surprises"])
    s = parse_html.html_set_line(s)
    s = get_price_changes(s, country, 'half_year')
    s = parse_html.html_text(s, ["Yearly Price Surprises"])
    s = parse_html.html_set_line(s)
    s = get_price_changes(s, country, 'year')
    f = open("/tmp/test.html","w")
    f.write(s)
    f.close()
    subject='%s: Price Surprises: %r' %(country, str(datetime.datetime.now().date()))
    send_email2('petlafin@gmail.com', 'Tasche3#Gm', 'petlafin@gmail.com', subject, s)

def price_surprises(country, change_percent, criteria, db_type, excel_type):
    print("Criteria: %r" %(criteria))
    if excel_type == 'EXCEL':
        xl = xlwt.Workbook()

        yr_sheet = xl.add_sheet("365 days change")
        qr_sheet = xl.add_sheet("90 days change")
        mon_sheet = xl.add_sheet("30 days change")
        week_sheet = xl.add_sheet("7 days change")
        day_sheet = xl.add_sheet("one day change")

        excel.add_price_surprise_header(yr_sheet, 'YEAR')
        excel.add_price_surprise_header(qr_sheet, 'QUARTER')
        excel.add_price_surprise_header(mon_sheet, 'MONTH')
        excel.add_price_surprise_header(week_sheet, 'WEEK')
        excel.add_price_surprise_header(day_sheet, 'DAY')
    else:
        xl = None

    db = DB.open_db('Stocks')
    if country == 'US':
        col = db['US_Stocks']
        #for doc in col.find({"bscs.industry":"Accident &Health Insurance"}):
        #for doc in col.find({}):
        #docs = col.find({"bscs.symbol":"HEXO"}).sort([["sno",1]])
        docs = col.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]])
        print("Count: %r" %(docs.count()))
        i=0
        len_skip= dcf_skip = price_skip = trading_skip = vol_skip = 0
        for doc in docs:
            #last_sno = int(read_from_file("price_surprise.txt"))
            sno = doc['sno']
            #if last_sno == docs.count():
            #    return
            #if sno < last_sno:
            #    print("Skipping %r: %r" %(sno, doc['bscs']['symbol']))
            #    continue
 
            #if sno > 2211:
            if sno > 0:
                doc['id'] = doc.pop('_id')
                #stock = DB.dbObject(**doc)
                stock = doc
                sym = doc['bscs']['symbol']
                name = doc['bscs']['name']
                #print("%r : "%(i), end = '')

                list=doc['num']
                if len(list) == 0:
                    len_skip+=1
                    continue
                if "dcf_years" not in list.keys():
                    dcf_skip+=1
                    continue
                if stock['bscs']['price'] < 1:
                    price_skip+=1
                    continue
                if stock['bscs']['trading'] != 'YES':
                    trading_skip+=1
                    continue
                if stock['bscs']['volume'] < 40000:
                    vol_skip+=1
                    continue
                i+=1
                print("%d: %d: %s: %s" %(i, sno, sym, name))
                if type(stock['num']['eps_20yr']) is int:
                    stock['num']['eps_20yr']=[]
                price_suprise(country, col, stock, sym, name, change_percent, xl, criteria, db_type, excel_type)
                #write_to_file(str(doc['sno']), "price_surprise.txt", "w")

        print("len_skip: %r, dcf_skip = %d, price_skip = %d, trading_skip = %d, vol_skip = %d" %(len_skip, dcf_skip, price_skip, trading_skip, vol_skip))
    elif country == 'India':
        col = db['India_Stocks']
        for doc in col.find({}):
            if i > -1:
                doc['id'] = doc.pop('_id')
                #stock = dbObject(**doc)
                stock = doc
                sym = doc['bscs']['symbol']
                name = doc['bscs']['name']
                sym = sym + '.BO'
                price_suprise(country, col, stock, sym, name, change_percent, xl, criteria, db_type, excel_type)
            i += 1
    
    #now = datetime.datetime.now().date()
    now = datetime.datetime.now()
    if excel_type == 'EXCEL':
        excel_file = "US_Stocks/DCF_Calc/price_surprises_%s.xls" % (str(now))
        #xl.save("US_Stocks/DCF_Calc/price_surprises.xls")
        xl.save(excel_file)


def get_price_volume(stk, country, vpn_event=None):
    #data = pdr.get_data_yahoo(symbols=stk['bscs']['symbol'], start=dt(2019,4,15), end=dt(2019,4,18))
    #stk['bscs']['price']  = round(float(data.iat[-1, data.columns.get_loc('Adj Close')]), 2)
    #vol = data[['Volume']]
    #sum = 0        
    #for v in vol.values.tolist():
    #    sum += v[0]
    #stk['bscs']['volume'] = sum / len(vol.values.tolist())
    
    ##data.get_quote_yahoo(stocklist).to_csv('test.csv', index=False, quoting=csv.QUOTE_NONNUMERIC)

    symbol = stk['bscs']['symbol'].replace('.','-')

    retries = 0
    conn_retries = 0
    while True:
        try:
            if vpn_event and vpn_event.is_set() is False:
                print("**** %s: Waiting..  VPN is changing" %(symbol))
                vpn_event.wait()
                print("**** %s: Waking up" %(symbol))

            if country == 'India':
                d = data.get_quote_yahoo(symbol+'.BO')
            elif country == 'US':
                d = data.get_quote_yahoo(symbol)
            else:
                PRINT_ERR("Unknown Country Name")
                return None
        except (KeyError, pdr._utils.RemoteDataError, IndexError) as E:
            PRINT_ERR("internet: %s:  Error, retrying" %(symbol))
            if vpn_event:
                if retries  > 5:
                    PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
                    DB.update_price_failcount(stk, country)
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
                if retries  > 5:
                    PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
                    DB.update_price_failcount(stk, country)
                    return None
                retries = retries + 1
                time.sleep(2)
                continue
        #except (urllib3.exceptions.NewConnectionError, OpenSSL.SSL.SysCallError) as E:
        except Exception as E:
            if conn_retries > 5:
                PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
                return None
            PRINT_ERR("%s: Connection Error, retrying" %(symbol))
            time.sleep(1)
            conn_retries = conn_retries + 1
            continue
 
        #except pdr._utils.RemoteDataError:
        #    PRINT_ERR("Unable to get data for %s: %s"%(stk['bscs']['name'], stk['bscs']['symbol']))
        #    if retries  > 5:
        #        return None
        #    change_vpn()
        #    retries = retries + 1
        #    continue
        #except IndexError:
        #    PRINT_ERR("Unable to get price and volume for %s"%(stk['bscs']['symbol']))
        #    if retries  > 5:
        #        return None
        #    change_vpn()
        #    retries = retries + 1
        #    continue
        try:
            # Add moving average etc. Refer /tmp/test.csv for details
            if 'regularMarketVolume' in d.keys():
                stk['bscs']['volume'] = (d['regularMarketVolume'][0])
            elif 'averageDailyVolume3Month' in d.keys():
                stk['bscs']['volume'] = (d['averageDailyVolume3Month'][0])
            else:
                stk['bscs']['volume'] = 0
            if 'marketCap' in d.keys():
                if country == 'India':
                    stk['bscs']['mcap']   = float(d['marketCap'][0])/10000000 # in crores
                else:
                    stk['bscs']['mcap']   = float(d['marketCap'][0])/1000000 # in millions
            else:
                stk['bscs']['mcap'] = 0

            stk['bscs']['price']  = (d.price.to_list()[0])
            if 'sharesOutstanding' in d.keys():
                stk['bscs']['outstanding_shares'] = d['sharesOutstanding'][0]
            else:
                stk['bscs']['outstanding_shares'] = 0
            if 'longName' in d.keys():
                stk['bscs']['Name'] = d.iloc[0]['longName']
            elif 'shortName' in d.keys():
                stk['bscs']['Name'] = d.iloc[0]['shortName']
            if 'fullExchangeName' in d.keys():
                stk['bscs']['exchange_name'] = d.iloc[0]['fullExchangeName']

        except AttributeError as e:
            if 'outstanding_shares' not in stk['bscs'].keys():
                stk['bscs']['outstanding_shares'] = 0
            if 'volume' not in stk['bscs'].keys():
                stk['bscs']['volume'] = 0
            PRINT_ERR(str(e))
            PRINT_ERR("Couldn't get a particular field for %s" %(stk['bscs']['symbol']))
        break
    print("internet: %s: %s"%(stk['bscs']['symbol'],stk['bscs']['name']))
    return stk

def get_price_growth(country, stk, years, data_type):
    if stk['bscs']['price_years'] != 5 and stk['bscs']['price_years'] != 10 and stk['bscs']['price_years'] != 0:
        yrs = int(stk['bscs']['price_years'])
    else:
        yrs = years

    if data_type == 'HOT':
        end = dt.today()
        st = dt(end.year-years, end.month, end.day)
        print("start: %s, end: %s" %(st.date(), end.date()))
        try:
            data = pdr.DataReader(stk['bscs']['symbol'], 'yahoo', st, end)
        except pdr._utils.RemoteDataError:
            PRINT_ERR("Unable to get data for %s: %s"%(stk['bscs']['name'], stk['bscs']['symbol']))
            stk['bscs']['hist_price_5'] = 1
            stk['bscs']['hist_price_10'] = 1
            return 0

        st_price = data.iat[0, data.columns.get_loc('Close')]
        en_price = data.iat[-1, data.columns.get_loc('Close')]
        yrs = end.year - int(str(list(data.index)[0]).split('-')[0])
        print("yrs: %d, %s" %(yrs, str(list(data.index)[0]).split('-')[0]))
        del data
        if years <= 5:
            stk['bscs']['hist_price_5'] = st_price
        else:
            end = dt.today()
            st = dt(end.year-5, end.month, end.day)
            data = pdr.DataReader(stk['bscs']['symbol'], 'yahoo', st, end)
            stk['bscs']['hist_price_5'] = data.iat[0, data.columns.get_loc('Close')]
            del data
 
        if years > 5 and years <= 10:
            stk['bscs']['hist_price_10'] = st_price
        else:
            end = dt.today()
            st = dt(end.year-10, end.month, end.day)
            data = pdr.DataReader(stk['bscs']['symbol'], 'yahoo', st, end)
            stk['bscs']['hist_price_10'] = data.iat[0, data.columns.get_loc('Close')]
            del data

        db = DB.open_db('Stocks')
        if country  == 'US':
            collection = db['US_Stocks']
        elif country == 'India':
            collection = db['India_Stocks']
        else:
            raise exception("Unknown Country Name %s" %(country))

        DB.update_field(collection, stk['bscs']['symbol'], "bscs.hist_price_5", stk['bscs']['hist_price_5'])
        DB.update_field(collection, stk['bscs']['symbol'], "bscs.hist_price_10", stk['bscs']['hist_price_10'])
        DB.update_field(collection, stk['bscs']['symbol'], "bscs.price", round(en_price,2))
        DB.update_field(collection, stk['bscs']['symbol'], "bscs.price_years", yrs)
 
    if yrs < 1:
        yrs = 1
    if years == 10:
        st_price = stk['bscs']['hist_price_10']
    else:
        st_price = stk['bscs']['hist_price_5']

    en_price = stk['bscs']['price']
    #    st_price = round(float(st_price.real),2)
    #if isinstance(en_price, complex):
    #    en_price = rount(float(en_price.real),2)
    years = yrs
    try:
        growth = round(((en_price/st_price)**(1/years)-1), 2)
    except ZeroDivisionError:
        growth = 0
    PRINT("years: %d, growth: %r" %(years, growth))
    return growth

# Get stock split information
def get_stock_split_info_yahoo(country, stk):
    if country == 'India':
        sym = stk['bscs']['symbol'] + '.BO'
    elif country != 'US':
        PRINT_ERR("Unknown Country")
        return
    #get split info from Yahoo Finance
    data = yf(sym).get_key_statistics_data()
    stk['bscs']['split_factor'] = float(Fraction(data[sym]['lastSplitFactor']))
    d = data[sym]['lastSplitDate']
    stk['bscs']['split_date'] = d
    stk['bscs']['split_year'] = datetime.datetime.strptime(d, '%Y-%m-%d').year 

def get_LTP(country, sym):
    sym1 = sym
    if country == 'India':
        sym = sym + '.BO'
    elif country != 'US':
        PRINT_ERR("Unknown Country")
        return 0
    #price = yf(sym).get_current_price()
    price = data.get_quote_yahoo(sym).iloc[0]['price']
    if not price and '.' in sym:
        sym = sym.replace('.', '-')
        price = yf(sym).get_current_price()
    if not price:
        PRINT_ERR("Unable to get latest price for %s" %(sym))
        PRINT_ERR("Updating stock to not trading")
        db = DB.open_db('Stocks')
        if country == 'US':
            col = db.US_Stocks
        elif country == 'India':
            col = db.India_Stocks
        else:
            return 0
        #DB.update_field(col, sym1, "bscs.trading", "NO")
        return 0
    return price

def get_page(url, html_file):
    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0"}
    html=requests.get(url, headers=headers)
    if html.status_code == 200:
        write_to_file(html.text, html_file)
    else:
        PRINT_ERR("Couldnt get page : %s" %(url))

def get_webpage(url):
    headers={"User-Agent":"Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:69.0) Gecko/20100101 Firefox/69.0"}
    return requests.get(url, headers=headers).text

def browse_US_stock_page(stock, url):
    driver = webdriver.Firefox()
    driver.set_page_load_timeout(30)
    driver.get(url)
    old_url = driver.current_url
    driver.maximize_window()

    time.sleep(5)
    elem = driver.find_element_by_class_name("panclose5084")
    if elem:
        elem.click()
    return
    elem = driver.find_element_by_class_name("bc-button white-button small settings-button")
    elem.click()
    time.sleep(20)
    driver.close()

        # attr=driver.find_element_by_name('txtStock').get_attribute('innerHTML')
        # attr=elem.get_attribute('innerHTML')
    # elem.send_keys(stock, Keys.ARROW_DOWN)
    # time.sleep(2)
    # elem.send_keys(Keys.RETURN)

"""
    # time.sleep(20)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(
            (By.ID, 'lblCompany')))
    except TimeoutException:
        PRINT("Unable to parse %r" % (stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
        return
    # PRINT_DBG(str(html_src))

    if driver.current_url == old_url:
        PRINT("Unable to parse %r" % (stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        # PRINT_DBG("Found stock %r" %(stock))
        html_src = driver.page_source
        html_file = "html_pages/%s.html" % (stock_name)
        f = open(html_file, "w")
        f.write(html_src)
        f.close()
"""
    #    try:
    #        element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
    #        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, 'IdOfMyElement')))
    #        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
    #        html_file = "html_pages/%s.html" %(stock)
    #        f = open(html_file, "w")
    #        f.write(html_src)
    #        f.close()
    #    finally:
    #        PRINT_DBG("Unable to parse %r" %(stock))
    #        f = open("unparsed_stocks.txt", "a")
    #        f.write(stock)
    #        f.write("\n")
    #        f.close()

    #driver.close()

    # try:
    #    element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
    # finally:
    #    driver.close()

    # assert "No results found." not in driver.page_source
    # time.sleep(5)

def get_US_earnings_estimates(symbol, name):
    driver = webdriver.Firefox()
    driver.set_page_load_timeout(30)

    url = "https://www.barchart.com/stocks/quotes/%s/earnings-estimates" %(symbol)
    
    driver.get(url)
    old_url = driver.current_url
    driver.maximize_window()

    html_file = "%s/%s_earnings_estimates.html" %(path, symbol)
    get_page(url, html_file)
    return 

def update_DB_US_earnings_estimates(stk, earnings, fiftytwoweek_high, fiftytwoweek_low):
    db = DB.open_db('Stocks')
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.fiftytwoweek_high", fiftytwoweek_high)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.fiftytwoweek_low", fiftytwoweek_low)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.date", earnings.date)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.high_target", earnings.high_target)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.mean_target", earnings.mean_target)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.low_target", earnings.low_target)

    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.hist.quarters", earnings.hist.quarters)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.hist.reported", earnings.hist.reported)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.hist.estimate", earnings.hist.estimate)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.hist.difference", earnings.hist.difference)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.hist.surprise", earnings.hist.surprise)

    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.quarters", earnings.est.quarters)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.years", earnings.est.years)

    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.q_avg_est", earnings.est.q_avg_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.q_num_est", earnings.est.q_num_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.q_high_est", earnings.est.q_high_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.q_low_est", earnings.est.q_low_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.q_prior_yr", earnings.est.q_prior_yr)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.q_gr_rate", earnings.est.q_gr_rate)

    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.y_avg_est", earnings.est.y_avg_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.y_num_est", earnings.est.y_num_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.y_high_est", earnings.est.y_high_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.y_low_est", earnings.est.y_low_est)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.y_prior_yr", earnings.est.y_prior_yr)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "quart_fig.Earning_Estimates.est.y_gr_rate", earnings.est.y_gr_rate)

def click_sym(symbol, elem):
    print(len(elem))
    
def populate_US_earnings_estimates(stk):
    earnings = Earnings()

    url = "https://www.barchart.com/stocks/quotes/%s/earnings-estimates" %(stk['bscs']['symbol'])
    br = open_browser('headless')
    try:
        br.get(url)
    except Exception:
        print("%s: %s webpage loading timeout, trying again" %(stk['bscs']['symbol'], stk['bscs']['name']))
        close_browser(br)
        time.sleep(5)
        br = open_browser()
        br.get(url)

    #time.sleep(5)
    #ad popup
    try:
        e = br.find_element_by_xpath("/html/body/div[8]/div[2]/div[1]")
        e.click()
    except Exception:
        PRINT("No popup")

    try:
        page = br.page_source
    except Exception as e:
        print("%s: %s page source exception trying again, err: %s" %(stk['bscs']['symbol'], stk['bscs']['name'], str(e)))
        time.sleep(5)
        br.get(url)
        page = br.page_source

    soup = parse_html.get_soup(page)

    if soup.find("title").text.lstrip().rstrip() == 'Page not found':
        PRINT_ERR("%s:%s Invalid page, skipping" %(stk['bscs']['symbol'], stk['bscs']['name']))
        update_DB_US_earnings_estimates(stk, earnings, stk['bscs']['price'], stk['bscs']['price'])
        close_browser(br)
        return

    msg = ' Earnings are not available for %s.  ' %(stk['bscs']['symbol'])
    pattern = re.compile(r'%s'%msg)
    div = soup.find(text=pattern)
    if div:
        PRINT_ERR("%s:%s does not have earnings estimates, skipping" %(stk['bscs']['symbol'], stk['bscs']['name']))
        update_DB_US_earnings_estimates(stk, earnings, stk['bscs']['price'], stk['bscs']['price'])
        close_browser(br)
        return
    
    l=soup.find(text=re.compile('^HIGH TARGET '))
    earnings.high_target = str_to_float(l.parent.text.split(' ')[-1])
    l=soup.find(text=re.compile('^LOW TARGET '))
    earnings.low_target = str_to_float(l.parent.text.split(' ')[-1])
    l=soup.find(text=re.compile('^MEAN TARGET '))
    earnings.mean_target = str_to_float(l.parent.text.split(' ')[-1])

    l=soup.find(text=re.compile('^52 WK High '))
    fiftytwoweek_high = str_to_float(l.parent.text.split(' ')[-1])
    l=soup.find(text=re.compile('^52 WK Low '))
    fiftytwoweek_low = str_to_float(l.parent.text.split(' ')[-1])


    l = soup.find("span", {"class": "last-change"})
    #l = soup.find("span", {"class": "last-change ng-binding"})
    DB.update_field(DB.open_db('Stocks').US_Stocks, stk['bscs']['symbol'], "bscs.price", str_to_float(l.text))

    l=soup.find_all(text=re.compile('^Qtr Ending'))
    for entry in l:
        earnings.hist.quarters.append(entry.parent.parent.text.split(' ')[3])

    l=soup.find(text=re.compile('^Reported'))
    entries=l.parent.parent.parent.text.split(' ')
    for entry in entries[5:-1]:
        if entry != '':
            earnings.hist.reported.append(str_to_float(entry))

    l=soup.find(text=re.compile('^Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    for entry in entries[5:-1]:
        if entry != '':
            earnings.hist.estimate.append(str_to_float(entry))

    for i in range(len(earnings.hist.estimate)):
        est = earnings.hist.estimate[i]
        rep = earnings.hist.reported[i]
        try:
            earnings.hist.difference.append(round(rep-est,3))
        except Exception as e:
            earnings.hist.difference.append(float('NaN'))
        try:
            earnings.hist.surprise.append(round(((rep - est)/ est), 4))
        except Exception as e:
            earnings.hist.surprise.append(float('NaN'))

    l=soup.find(text=re.compile('^Current Qtr'))
    earnings.est.quarters.append(l.parent.parent.text.split(' ')[-2])
    l=soup.find(text=re.compile('^Next Qtr'))
    earnings.est.quarters.append(l.parent.parent.text.split(' ')[-2])
    l=soup.find_all(text=re.compile('^Fiscal Yr'))
    earnings.est.years.append(l[0].parent.parent.text.split(' ')[-2])
    earnings.est.years.append(l[1].parent.parent.text.split(' ')[-2])

    l=soup.find(text=re.compile('^Average Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_avg_est.append(str_to_float(entry))
            else:
                earnings.est.y_avg_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Number of Estimates'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_num_est.append(str_to_float(entry))
            else:
                earnings.est.y_num_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^High Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_high_est.append(str_to_float(entry))
            else:
                earnings.est.y_high_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Low Estimate'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_low_est.append(str_to_float(entry))
            else:
                earnings.est.y_low_est.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Prior Year'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[5:-1]:
        if entry != '':
            if count < 2:
                earnings.est.q_prior_yr.append(str_to_float(entry))
            else:
                earnings.est.y_prior_yr.append(str_to_float(entry))
            count += 1

    l=soup.find(text=re.compile('^Growth Rate Est'))
    entries=l.parent.parent.parent.text.split(' ')
    count=0
    for entry in entries[14:-1]:
        if entry != '':
            if entry == 'unch':
                entry = '0'
            if count < 2:
                earnings.est.q_gr_rate.append(round(str_to_float(entry)/100,4))
            else:
                earnings.est.y_gr_rate.append(round(str_to_float(entry)/100,4))
            count += 1

    earnings.date=str(dt.now().date())
    earnings.hist.quarters.reverse()
    earnings.hist.reported.reverse()
    earnings.hist.estimate.reverse()
    earnings.hist.difference.reverse()
    earnings.hist.surprise.reverse()

    #elem = br.find_element_by_name("search")
    #elem.send_keys("FIVE")
    ##time.sleep(10)
    ##page = br.page_source
    ##f=open("/tmp/five.html", "w")
    ##f.write(soup.prettify())
    ##f.close()
    #opts = WebDriverWait(br, 10).until(EC.presence_of_element_located(
    #        (By.CLASS_NAME, 'quick-search')))
    ##elem = br.find_element_by_class_name("quick-search")

	#br.find_element_by_name("search").clear()
	#br.find_element_by_name("search").send_keys("Five Below")
	#br.find_element_by_name("search").send_keys(Keys.ARROW_DOWN)
	#br.find_element_by_name("search").send_keys(Keys.RETURN)

    #click_sym(stk['bscs']['symbol'], elem)
    #print("Opts: %r : %r" %(len(opts.text), opts.text))

    #return
 
    #try:
    #    e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div/div[1]")
    #    if e:
    #        s=e.text
    #        if s.find("Earnings are not available for") != -1:
    #            print("No data for %s: %s, skipping" %(stk['bscs']['symbol'], stk['bscs']['name']))
    #            return
    #except Exception as e:
    #    print(str(e))

    #try:
    #    e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[1]/div/div[1]/div/div/div/div[2]/div/p[1]")
    #    if e:
    #        print("Page does not exist for %s: %s, skipping" %(stk['bscs']['symbol'], stk['bscs']['name']))
    #        return
    #except Exception as e:
    #    print(str(e))


    #sign on popup
    #e = br.find_element_by_xpath("/html/body/div[9]/div/div/div[1]/div/i")
    #e.click()

    # date
    #e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[1]/div[4]/span[2]")
    #date=timestring.Date(e.text)
    #date=date.date
    #date=str(date.date())
    #earnings.date=date
    ##earnings.date=str(dt.now().date())

    ###high target
    ##e = br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[1]/div[1]/span")
    ##earnings.high_target = str_to_float(e.text)
    ##
    ###mean target
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[1]/div[2]/span")
    ##earnings.mean_target = str_to_float(e.text)
    ###low target
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[1]/div[3]/span")
    ##earnings.low_target=str_to_float(e.text)
    ###52 week high
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[2]/div[1]/span")
    ##earnings.fiftytwoweek_high=str_to_float(e.text)
    ###52 week low
    ##e=br.find_element_by_xpath("/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[1]/symbol-chart/div/div[2]/span[2]/div[2]/span")
    ##earnings.fiftytwoweek_low=str_to_float(e.text)


    ###Earnings History
    ##for i in range(2,6):
    ##    #quarter dates
    ##    xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[1]/div/div[2]/div/div/ng-transclude/table/thead/tr/th[%d]/span[2]" %(i)
    ##    e = br.find_element_by_xpath(xpath)
    ##    earnings.hist.quarters.append(e.text)
    ##    #reported
    ##    xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[1]/div/div[2]/div/div/ng-transclude/table/tbody/tr[1]/td[%d]" %(i)
    ##    e = br.find_element_by_xpath(xpath)
    ##    rep = str_to_float(e.text)
    ##    earnings.hist.reported.append(rep)
    ##    #estimate
    ##    xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[2]/div[1]/div/div[2]/div/div/ng-transclude/table/tbody/tr[2]/td[%d]" %(i)
    ##    e = br.find_element_by_xpath(xpath)
    ##    est = str_to_float(e.text)
    ##    earnings.hist.estimate.append(est)
    ##    #difference
    ##    earnings.hist.difference.append(round(rep - est,2))
    ##    #surprise
    ##    try:
    ##        earnings.hist.surprise.append(round(((rep - est)/ est), 3))
    ##    except ZeroDivisionError:
    ##        earnings.hist.surprise.append(0)

    #Earnings Estimates
    ##for i in range(2,6):
    ##    if i < 4:
    ##        #quarter dates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/thead/tr/th[%d]/span[2]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.quarters.append(e.text)

    ##        #average estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[1]/td[%i]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_avg_est.append(str_to_float(e.text))
    ##
    ##        #number of estimates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[2]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_num_est.append(str_to_float(e.text))
    ## 
    ##        #high estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[3]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_high_est.append(str_to_float(e.text))
    ##
    ##        #low estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[4]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_low_est.append(str_to_float(e.text))
    ##
    ##        #prior year
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[5]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_prior_yr.append(str_to_float(e.text))
    ##
    ##        #growth rate estimate (yoy)
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[6]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.q_gr_rate.append(round(str_to_float(e.text)/100, 3))

    ##    else:
    ##        #year dates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/thead/tr/th[%d]/span[2]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.years.append(e.text)

    ##        #average estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[1]/td[%i]" %(i)
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_avg_est.append(str_to_float(e.text))
    ##
    ##        #number of estimates
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[2]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_num_est.append(str_to_float(e.text))
    ## 
    ##        #high estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[3]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_high_est.append(str_to_float(e.text))
    ##
    ##        #low estimate
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[4]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_low_est.append(str_to_float(e.text))
    ##
    ##        #prior year
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[5]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_prior_yr.append(str_to_float(e.text))
    ##
    ##        #growth rate estimate (yoy)
    ##        xpath = "/html/body/div[2]/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div[3]/div[1]/div[1]/div[2]/div/div/ng-transclude/table/tbody/tr[6]/td[%d]" %(i) 
    ##        e = br.find_element_by_xpath(xpath)
    ##        earnings.est.y_gr_rate.append(round(str_to_float(e.text)/100, 3))

    #print(earnings.date)
    #print(earnings.high_target)
    #print(earnings.mean_target)
    #print(earnings.low_target)

    #print("Historical data")
    #print("Quarters: %r" %(earnings.hist.quarters))
    #print("Reported: %r" %(earnings.hist.reported))
    #print("Estimate: %r" %(earnings.hist.estimate))
    #print("Difference: %r" %(earnings.hist.difference))
    #print("Surprise: %r" %(earnings.hist.surprise))

    #print("Estimates")
    #print("Quarters: %r" %(earnings.est.quarters))
    #print("Years: %r" %(earnings.est.years))
    #
    #print("Quarter Avg Est: %r" %(earnings.est.q_avg_est))
    #print("Quarter Num Est: %r" %(earnings.est.q_num_est))
    #print("Quarter High Est: %r" %(earnings.est.q_high_est))
    #print("Quarter Low Est: %r" %(earnings.est.q_low_est))
    #print("Quarter Prior Yr: %r" %(earnings.est.q_prior_yr))
    #print("Quarter Growth Rate: %r" %(earnings.est.q_gr_rate))

    #print("Year Avg Est: %r" %(earnings.est.y_avg_est))
    #print("Year Num Est: %r" %(earnings.est.y_num_est))
    #print("Year High Est: %r" %(earnings.est.y_high_est))
    #print("Year Low Est: %r" %(earnings.est.y_low_est))
    #print("Year Prior Yr: %r" %(earnings.est.y_prior_yr))
    #print("Year Growth Rate: %r" %(earnings.est.y_gr_rate))

    update_DB_US_earnings_estimates(stk, earnings, fiftytwoweek_high, fiftytwoweek_low)

    #get_US_earnings_chart(earnings, br)
    close_browser(br)


def get_val(br, description, convert):
    soup = BeautifulSoup(br.page_source, 'html.parser')
    f=open("/home/vpetla/avgo-chart.html","w")
    f.write(soup.prettify())
    f.close()
    try:
        e = soup.find("td", {"class": "field-value"})
        print("get_val(): %s: %s" % (description, e.text))
        if convert:
            return float(e.text)
        return e.text
        # print("%d: %s: %s" %(i, description, eps))
        # if i > 10:
        #    break
    except Exception as e:
        print("Exception occured:", str(e))
        if convert:
            return 10000
        #return "10000"

def get_price(description):
    return round(float(description.split(",")[-1][:-1]), 2)

def get_date(br, description):
    soup = BeautifulSoup(br.page_source, 'html.parser')
    e = soup.find("td", {"class": "field-value"})
    e = e.find_next("td", {"class": "field-value"})
    #return e.text
    try:
        date = dt.strptime(e.text, '%m/%d/%Y').date()
    except Exception:
        PRINT_ERR("Failed to get Date: %r", e.text)
        exit()
    return date
    #eps_date = description.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
    #eps_date = dt.strptime(eps_date, '%b %d %Y').date()
    #return str(eps_date)

perform_i=0
def perform(h):
    global perform_i
    try:
        perform_i +=1
        h.perform()
    except Exception as e:
        if perform_i > 0:
            print("h.perform() error")
            print(str(e))
            #exit()
            perform_i=0
            return False
        perform(h)
    perform_i=0
    return True

def scroll(br, direction):
    e=br.find_element_by_tag_name('html')
    for i in range(5):
        e.send_keys(direction)

def tab(br):
    print("tab")
    a = ac(br)
    a.send_keys(Keys.TAB).perform()

def popout_chart(br):
    try:
        a = ac(br)

        #Interactive chart
        we=br.find_element_by_class_name("bc-interactive-chart__wrapper-chart-content")
        h=a.move_to_element(we)
        h.context_click().perform()
        #soup=BeautifulSoup(br.page_source,'html.parser')
        #pattern=re.compile(r'Popout Chart')
        #e=soup.find(text=pattern)

        scroll(br, Keys.ARROW_DOWN)
        time.sleep(1)
        scroll(br, Keys.ARROW_DOWN)
        time.sleep(1)
        scroll(br, Keys.ARROW_DOWN)
        time.sleep(1)
        # Popout Chart
        we=br.find_element_by_css_selector("li.bc-interactive-chart-context-menu__menu-list-item:nth-child(28)")
        #we =br.find_element_by_css_selector("li.bc-interactive-chart-context-menu__menu-list-item:nth-child(28)")
        #we = br.find_element_by_class_name("bc-interactive-chart-context-menu__menu-list-item grouped margin-bottom-7")
        h=a.move_to_element(we)
        h.click().perform()
        WebDriverWait(br, 20).until(EC.number_of_windows_to_be(2))
        handles=br.window_handles
        br.switch_to_window(handles[0])
        br.close()
        br.switch_to_window(handles[-1])
    except Exception as E:
        exception_info(E)

def get_eps_for_element(br, description, convert, entries, offset, field, we, trial):
    entry = {}
    j = 0
    if trial == 1:
        a=ac(br)
        h = a.move_to_element(we)
        h.perform()
        time.sleep(0.1)
    while j in range(10):
        a = ac(br)
        val = get_val(br, description, convert)
        print("val:",val)
        if field == "split_factor":
            pattern=re.compile(r'\d{1,4}-\d{1,4}')
            #pattern=re.compile(r'^[1-9]*-[1-9]*')
            if pattern.match(val):
                split = round(float(val.split("-")[0])/float(val.split("-")[-1]), 3)
                entry[get_date(br, description)] = {"price":get_price(description), "split":val, field:split}
            entries.update(entry)
            return j
        elif val != 10000:
            entry[get_date(br,description)] = {"price":get_price(description), field:val}
            entries.update(entry)
            #print(entries)
            return j
        if trial:
            #print("height: %d" %(we.size['height']))
            #print("width: %d" %(we.size['width']))
            x_offset = we.size['height'] / 4 #+ j
            y_offset  = we.size['width'] / 4 #+ j
            #h = a.move_to_element_with_offset(we, x_offset, y_offset)
            h = a.move_by_offset(offset, offset)
            time.sleep(1)
        else:
            h = a.move_by_offset(offset, offset)
        perform(h)
        time.sleep(1)
        j += 1
    return j

def convert_date(label):
    date = None
    label = label.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
    try:
        date = dt.strptime(label, '%B %Y').date()
    except ValueError:
        print(date)
        date = dt.strptime(label, '%B %D %Y').date()
    if not date:
        print(date)
        sys.exit()
    return date

def get_all_entries(br, stk, item, field, pattern, convert):
    entries = {}
    entry = {}
    now = dt.now().date()
    start = dt.strptime("1950-01-01", '%Y-%m-%d').date()
    end = now

    if item not in stk['fig'].keys():
        stk['fig'][item]={}
    dates = list(stk['fig'][item].keys())
    last_date = get_last_date(stk, dates, '%Y-%m-%d')

    time.sleep(1)
    #scroll(br, Keys.ARROW_DOWN)

    # wire driver
    req = br.requests[-1]
    path = req.path
    if path.find('earnings=true'):
        earnings = response.body
        data = StringIO(earnings.decode('utf-8'))
        df = pd.read_csv(data, names=['Symbol','Date', 'Earnings','EPS'])

    else:
        return

    #soup = BeautifulSoup(br.page_source, 'html.parser')
    #tags = soup.find({"g"}, {"class":"#bc-interactive-chart__chart-container"})
    ##tags = soup.find({"g"}, {"class":"highcharts-series-group"})
    #labels = tags.findAll({"rect"})
    #start  = convert_date(str(labels[0].attrs['aria-label']))
    #end    = convert_date(str(labels[-1].attrs['aria-label']))

    db = DB.open_db('Stocks')
    if start < last_date:
        start = last_date + timedelta(7)
        end   = now
    #else:
    #    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.since", str(start))

    st = start
    while True:
        en = st + timedelta(days=365*10)
        if en >= now:
            en = now

        print("Selecting date")
        print("start: %s, end: %s" %(st, en))
        we = br.find_element_by_css_selector(".bc-glyph-calendar")
        we.click()
        d="%s/%s/%s"%(st.strftime('%m'), st.strftime('%d'), st.strftime('%Y'))
        #we = br.find_element_by_xpath("/html/body/div[6]/div/div/form/div[3]/div[1]/div/input")
        we = br.find_element_by_css_selector("div.interactive-chart-date-range:nth-child(1) > div:nth-child(1) > input:nth-child(1)")
        we.clear()
        we.click()
        we.send_keys(d)
        time.sleep(0.5)
        we.send_keys(Keys.TAB)
        d="%s/%s/%s"%(en.strftime('%m'), en.strftime('%d'), en.strftime('%Y'))
        #we = br.find_element_by_xpath("/html/body/div[6]/div/div/form/div[3]/div[2]/div/input")
        we = br.find_element_by_css_selector("div.interactive-chart-date-range:nth-child(3) > div:nth-child(1) > input:nth-child(1)")
        we.clear()
        we.click()
        we.send_keys(d)
        time.sleep(0.5)
        we.send_keys(Keys.TAB)
        #tab(br)
        #h=a.send_keys(d)
        #h.perform()
        br.find_element_by_css_selector("button.bc-button:nth-child(2)").click()
        time.sleep(2)
    
        soup = BeautifulSoup(br.page_source, 'html.parser')
        elements = soup.findAll(text=pattern)
   
        #a = ac(br)
        i = 0
        print("elements: %d" % (len(elements)))
        if len(elements) > 0:
            #description = elements[0].parent.parent.attrs['aria-label']
            #d1date = description.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
            #d1date = dt.strptime(d1date, '%b %d %Y').date()
    
            #description = elements[-1].parent.parent.attrs['aria-label']
            #d2date = description.rsplit(",", 1)[0].split(".")[-1].split(",", 1)[-1].lstrip().rstrip().replace(",", "")
            #d2date = dt.strptime(d2date, '%b %d %Y').date()
            ##d1date = datetime.strptime(d1, '%m/%d/%Y')
            ##d2date = datetime.strptime(d2, '%m/%d/%Y')
            #print(d1date)
            #print(d2date)
            #if d1date > d2date:
            #    elements.reverse()
            #f = open("/home/vpetla/aapl-chart1.html","w")
            #f.write(soup.prettify())
            #f.close()
            #input("Press any key to continue")

            for e in elements:
                if i >= 0:
                    #print(e.parent.parent)
                    #if not 'fill' in e.parent.parent.attrs:
                    #    continue
                    description = e.parent.parent.attrs['aria-label']
                    #print("Description:", description)
                    #print("Parent:",e.parent.parent)
                    attr = "g[aria-label=\'%s\'" % (description)
                    we = br.find_element(By.CSS_SELECTOR, attr)
                    #print("Web Element:", we)
                    a=ac(br)
                    h = a.move_to_element(we)
                    time.sleep(1)
                    # h = a.move_to_element_with_offset(we,0,0)
                    #print("Hovering to element")
                    if perform(h) is False:
                        print("Skipping %s" %(description))
                        continue
                    else:
                        #print("Hover Successfull")
                        pass
                    h=a=None
                    time.sleep(1)
                    offset = -1
                    j = get_eps_for_element(br, description, convert, entries, offset, field, we, 0)
                    if j == 20:
                        PRINT_ERR("%s: Couldn't get Value for : %r, checking the other way" %(stk['bscs']['symbol'], description))
                        offset = 1
                        a=ac(br)
                        h = a.move_to_element(we)
                        h.perform()
                        j = get_eps_for_element(br, description, convert, entries, offset, field, we, 1)
                        if j == 20:
                            PRINT_ERR("%s: Couldn't get Value for : %r, writing 100000" %(stk['bscs']['symbol'], description))
                            entry = {}
                            if field == "split_factor":
                                entry[get_date(br, description)] = {"price":get_price(description), "split":"100000:100000", field:100000}
                            else:
                                entry[get_date(br,description)] = {"price":get_price(description), field:100000}
                            entries.update(entry)
                            #exit()
                        #e={}
                        #return e
                i += 1
        st = en
        if en >= now:
            break
        if en >= end:
            break

    pp = pprint.PrettyPrinter(indent=4)
    sorted_entries = stk['fig'][item]
    for e in sorted(entries.keys()):
        sorted_entries[str(e)] = entries[e]
    sorted_entries['date'] = str(now)
    #pp.pprint(sorted_entries)
    scroll(br, Keys.ARROW_UP)
    return sorted_entries

def thread_click(e, lock):
    if e:
        lock.acquire()
        try:
            e.click()
        finally:
            lock.release()
 
def thread_close_popups(br, lock):
    while True:
        e = None
        print("looping close_popups")
        if stop_thread:
            break
        try:
            e = br.find_element_by_xpath("/html/body/div[8]/div[2]/div[1]")
            thread_click(e, lock)
        except Exception:
            pass
        try:
            # e=br.find_element_by_xpath("//*[@id="ic_guyoff6702"]")
            e = br.find_element_by_xpath("/html/body/div[9]/div[2]/div[3]/div/img")
            thread_click(e, lock)
        except Exception as E:
           pass
        try:
            e = br.find_element_by_class_name("hide-for-small hide-for-medium-only")
            thread_click(e, lock)
        except Exception as E:
           pass
        try:
            e = br.find_element_by_css_selector(".form-close-wrapper > i:nth-child(1)")
            thread_click(e, lock)
        except Exception as E:
           pass
        try:
            e = br.find_element_by_css_selector("#off9609")
            thread_click(e, lock)
        except Exception as E:
           pass
 
        time.sleep(1)

def close_login(br):
    try:
        br.switch_to_window(handles[-1])
        br.close()
        br.switch_to_window(handles[0])
    except:
        pass

def click(e):
    try:
        e.click()
    except ElementClickInterceptedException:
        close_login(br)

def find_element_by_css_selector(br, select):
    try:
        return br.find_element_by_css_selector(select)
    except Exception as e:
        print("Failed to find element by css selector")
        print(str(e))
        soup=BeautifulSoup(br.page_source,"html.parser")
        f=open("/home/vpetla/stock-chart.html","w")
        f.write(soup.prettify())
        f.close()
        exit()

def toggle_earnings_button(br):
    # goto settings
    e = find_element_by_css_selector(br, "span.show-for-medium-up")
    click(e)
    # goto adjustments
    e = find_element_by_css_selector(br, "div.bc-tabs__tab:nth-child(3)")
    click(e)

    # select earnings
    e = find_element_by_css_selector(br,
        ".row-events > ul:nth-child(2) > li:nth-child(2) > div:nth-child(1) > label:nth-child(2)")
    click(e)

    # apply
    e = find_element_by_css_selector(br, "button.bc-button:nth-child(2)")
    click(e)

def toggle_dividend_button(br):
    # goto settings
    e = find_element_by_css_selector(br, "span.show-for-medium-up")
    click(e)

    # goto adjustments
    e = find_element_by_css_selector(br, "div.bc-tabs__tab:nth-child(3)")
    click(e)

    # select dividend
    e = find_element_by_css_selector(br,
        ".row-events > ul:nth-child(2) > li:nth-child(1) > div:nth-child(1) > label:nth-child(2)")
    click(e)

    # apply
    e = find_element_by_css_selector(br, "button.bc-button:nth-child(2)")
    click(e)

def toggle_split_button(br):
    # goto settings
    e = find_element_by_css_selector(br, "span.show-for-medium-up")
    click(e)

    # goto adjustments
    e = find_element_by_css_selector(br, "div.bc-tabs__tab:nth-child(3)")
    click(e)

    # select split
    e = find_element_by_css_selector(br,
        ".row-events > ul:nth-child(2) > li:nth-child(3) > div:nth-child(1) > label:nth-child(2)")
    click(e)

    # apply
    e = find_element_by_css_selector(br, "button.bc-button:nth-child(2)")
    click(e)

def set_max_range(br, stk):
    try:
        # set 10 year range
        # e = br.find_element_by_css_selector("div.quick-settings:nth-child(2) > ul:nth-child(1) > li:nth-child(11)")
        # set MAX range
        e = br.find_element_by_css_selector("div.quick-settings:nth-child(2) > ul:nth-child(1) > li:nth-child(13)")
        e.click()
    except Exception as e:
        print(str(e))
        stk_file="/home/vpetla/%s-chart.html" %(stk['bscs']['symbol'])
        soup=BeautifulSoup(br.page_source,"html.parser")
        f=open(stk_file,"w")
        f.write(soup.prettify())
        f.close()
        return False

def write_hist_to_db(stk, eps_hist, dividend_hist, split_hist):
    db = DB.open_db('Stocks')
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "fig.EPS_History", eps_hist)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "fig.DIVIDEND_History", dividend_hist)
    DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "fig.SPLIT_History", split_hist)

# field can be earnings, dividends, splits
def populate_entries(br, mysql_engine, field):
    try:
        column = {"earnings":"EPS", "dividends":"DIVIDEND", "splits":"SPLIT"}
        table = {'earnings':'EPS_History', 'dividends': 'DIVIDEND_History', 'splits':'SPLIT_History'}

        for i in reversed(range(len(br.requests))):
            path = br.requests[i].path
            if path.find('{}=true'.format(field)) > 0:
                field_data = br.requests[i].response.body
                break
        if i == 0:
            print("Couldn't find the response for field: %r"%(field))
            return

        data = StringIO(field_data.decode('utf-8'))

        df = pd.read_csv(data, names=['Symbol','Date', 'junk', column[field]])
        del df['junk']

        if not df.empty:
            if mysql_engine.has_table(table[field]):
                query = 'select * from {}'.format(table[field])
                ddf = DB.read_from_sql(query, mysql_engine, date=False)
                if not ddf.empty:
                    df = df[~df.Date.isin(ddf.Date)]
 
            DB.mysql_update_table(mysql_engine, table[field], df, check=True, insert=True, unknown_table=True, cols_type='fin', temp=True, date_column=False, format_columns=False)
    except Exception as E:
        exception_info(E)

stop_thread=False

def close_popups(br):
    global stop_thread
    while True:
        if stop_thread:
            print("Exiting thread")
            break
        e = None
        try:
            e = br.find_element_by_xpath("/html/body/div[8]/div[2]/div[1]")
            if e:
                print("Closed popup")
                e.click()
        except Exception:
            pass
        try:
            # e=br.find_element_by_xpath("//*[@id="ic_guyoff6702"]")
            e = br.find_element_by_xpath("/html/body/div[9]/div[2]/div[3]/div/img")
            if e:
                print("Closed popup")
                e.click()
        except Exception as E:
           pass
        try:
            e = br.find_element_by_class_name("hide-for-small hide-for-medium-only")
            if e:
                print("Closed popup")
                e.click()
        except Exception as E:
           pass
        try:
            e = br.find_element_by_css_selector(".form-close-wrapper > i:nth-child(1)")
            if e:
                print("Closed popup")
                e.click()
        except Exception as E:
           pass
        try:
            e = br.find_element_by_css_selector("#off9609")
            if e:
                print("Closed popup")
                e.click()
        except Exception as E:
           pass
 
    print("Exiting thread")

def populate_US_EPS(stk, mysql_engine=None, db=None):
    #if 'EPS_DIV_SPLIT_History_Date' in stk['bscs'].keys():
    #    last_date = stk['bscs']['EPS_DIV_SPLIT_History_Date']
    #    if (dt.now() - last_date) < timedelta(30):
    #        print("Already updated on %r" %(str(last_date.date())))
    #        return
    global stop_thread

    try:
        mysql_engine_created=False
        mongodb_engine_created=False
        if not mysql_engine:
            mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Fin')
            mysql_engine_created=True
        if not db:
            c  = open_db_client()
            db = c['Stocks']
            mongodb_engine_created=True

        fig = 'fig'
        #if not 'EPS_History' in stk[fig].keys():
        #    stk[fig]['EPS_History'] = {}

        #dates = list(stk[fig]['EPS_History'].keys())
        #dates.reverse()
        #if 'date' in dates:
        #    now = dt.now().date()
        #    last_date = stk[fig]['EPS_History']['date']
        #    last_date = dt.strptime(last_date, "%Y-%m-%d").date()
        #    if (dt.now().date() - last_date) < timedelta(30):
        #        print("Already updated on %r" %(str(last_date)))
        #        return


        #eps_hist = {}
        #split_hist = {}
        #dividend_hist = {}

        url = "https://www.barchart.com/stocks/quotes/%s/interactive-chart" %(stk['bscs']['symbol'])
        br = open_browser('headless', wiredriver=True)

        try:
            br.get(url)
        except Exception:
            print("%s: %s webpage loading timeout, trying again" %(stk['bscs']['symbol'], stk['bscs']['name']))
            close_browser(br)
            time.sleep(5)
            br = open_browser()
            br.get(url)

        stop_thread=False
        th = threading.Thread(target=close_popups, args=(br, ))
        th.start()

        # try:
        #    e=br.find_element_by_xpath("//*[@id="off7131"]")
        #    if e:
        #        e.click()

        # set 10 year range
        #e = br.find_element_by_css_selector("div.quick-settings:nth-child(2) > ul:nth-child(1) > li:nth-child(11)")
        time.sleep(4)
        
        if set_max_range(br, stk) is False:
            ##db = DB.open_db('Stocks')
            ##DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "ignore", "Yes")
            #write_hist_to_db(stk, eps_hist, dividend_hist, split_hist)
            #close_browser(br)
            gc.collect()
            if mysql_engine_created:
                DB.close_mysql_connection(mysql_engine)
            return
            
        br.maximize_window()
        time.sleep(2)

        # Cookies policy pop-up. Close it
        try:
            br.find_element_by_css_selector(".closebutton_closeButton--3abym > svg:nth-child(1) > path:nth-child(1)").click()
        except:
            pass
        time.sleep(1)
        popout_chart(br)
        #br.maximize_window()
        try:
            opts = WebDriverWait(br, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.bc-interactive-chart__wrapper-chart-content')))
            #opts = WebDriverWait(br, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.highcharts-background')))
        except selenium.common.exceptions.TimeoutException:
            pass
        print("chart loaded")
        time.sleep(4)

        toggle_earnings_button(br)
        time.sleep(3)
        populate_entries(br, mysql_engine, 'earnings')
        db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.EPS_History_Date": dt.now()}})
        #pattern = re.compile(r'^E$')
        #eps_hist = get_all_entries(br, stk, "EPS_History", "eps", pattern, 1)
        toggle_earnings_button(br)
        
        time.sleep(1)
        set_max_range(br, stk)
        time.sleep(2)
        toggle_dividend_button(br)
        time.sleep(3)
        populate_entries(br, mysql_engine, 'dividends')
        db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.DIVIDEND_History_Date": dt.now()}})
        #pattern = re.compile(r'^D$')
        #dividend_hist = get_all_entries(br, stk, "DIVIDEND_History", "dividend", pattern, 1)
        toggle_dividend_button(br)

        time.sleep(1)
        set_max_range(br, stk)
        time.sleep(2)
        toggle_split_button(br)
        time.sleep(3)
        populate_entries(br, mysql_engine, 'splits')
        db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.SPLIT_History_Date": dt.now()}})
        #pattern = re.compile(r'^S$')
        #split_hist = get_all_entries(br, stk, "SPLIT_History", "split_factor", pattern, 0)

        #write_hist_to_db(stk, eps_hist, dividend_hist, split_hist)

        db.US_Stocks.update({'bscs.symbol': stk['bscs']['symbol']}, {'$set': {"bscs.EPS_DIV_SPLIT_History_Date": dt.now()}})

        close_browser(br)
        if mysql_engine_created:
            DB.close_mysql_connection(mysql_engine)
        if mongodb_engine_created:
            DB.close_db_client(c)
        gc.collect()
    except Exception as E:
        exception_info(E)
    finally:
        print("Killing firefox")
        os.system('killall firefox')
        stop_thread=True
        th.join()

def get_page_with_check(url):
    html_page = get_webpage(url)
    #html_page  = get_html(html_file)
    soup = parse_html.get_soup(html_page)
    pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
    div = soup.find(text=pattern)
    if div:
        return None
    pattern = re.compile(r'Oops, something\'s wrong.')
    div = soup.find(text=pattern)
    if div:
        return None
    pattern = re.compile(r'Fundamentals')
    div = soup.find(text=pattern)
    if div:
        print("Going to overview page, breaking")
        return None
    return html_page

def get_pages(path, symbol, statement_type, duration_type):
    print(statement_type, duration_type)
    i=1
    trials = 0
    while True:
        url = "https://www.barchart.com/stocks/quotes/%s/%s/%s?reportPage=%s" %(symbol, statement_type, duration_type, i)
        html_file = "%s/%s_%s_%s_%s.html" %(path, symbol, statement_type, duration_type, i)
        html_page = get_webpage(url)
        #html_page  = get_html(html_file)
        soup = parse_html.get_soup(html_page)
        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
        div = soup.find(text=pattern)
        if div:
            break
        pattern = re.compile(r'Oops, something\'s wrong.')
        div = soup.find(text=pattern)
        if div:
            break
        pattern = re.compile(r'Fundamentals')
        div = soup.find(text=pattern)
        if div:
            print("Going to overview page, breaking")
            break

        if 'Financial data is not available' in html_page:
            print("Reached till no data is available")
            break
 
        if '403 ERROR' in html_page:
            PRINT_ERR("*********************** Access to Barchart blocked ******************, changing VPN")
            time.sleep(5)
            change_vpn()
            trials = trials + 1
            if trials > 5:
                PRINT_ERR("Changing VPN didn't work")
                PRINT_ERR("exiting")
                sys.exit(1)
            else:
                continue

        write_to_file(html_page, html_file)
        i = i + 1
        if  i > 100:
            print(" ERROR: Going to infinite loop")
            break
 
def get_US_stock_page(symbol, name):
    path = "/home/vpetla/work/stockanalysis/US_Stocks/html_pages/%s" %(name)
    path = path.lstrip().rstrip().replace(",","")
    try:
        os.makedirs(path, exist_ok=True)
    except FileExistsError:
        PRINT_ERR("%s exists" %(symbol))
        return

    #income statements
    get_pages(path, symbol, "income-statement", "annual")
    get_pages(path, symbol, "income-statement", "quarterly")
    #cash flow statements
    get_pages(path, symbol, "cash-flow", "annual")
    get_pages(path, symbol, "cash-flow", "quarterly")
    #balance sheet statements
    get_pages(path, symbol, "balance-sheet", "annual")
    get_pages(path, symbol, "balance-sheet", "quarterly")

    #url = "https://www.barchart.com/stocks/quotes/%s/profile" %(symbol)
    #html_file = "%s/%s_profile.html" %(path, symbol)
    #get_page(url, html_file)

    return path

def get_all_US_html_pages():
    db = open_db('Stocks')
    docs = db.US_Stocks_List.find({})
    for i, doc in enumerate(docs):
        if i > -1:
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

            print("%d: %s: %s "%(i, sym, name))
            get_US_stock_page(sym, name)

def get_html(stock_page):
    try:
        html = open(stock_page)
    except FileNotFoundError:
        PRINT_ERR("Failed to open %s" %(stock_page))
        return None
    return html

def get_India_stock_page(stock):
    driver = webdriver.Firefox()
    driver.get("http://www.ratestar.in/home")
    old_url = driver.current_url
    elem = driver.find_element_by_name("txtStock")

    elem.clear()
    for i in range(len(stock)):
        elem.send_keys(str(stock[i]))
        time.sleep(10/1000)
        #divs = driver.find_element_by_xpath()
        #s = Select(elem)
        #driver.find_element_by_css_selector("button.btn.btn-default").click()
        opts = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.ID, 'listPlacementStock')))
        time.sleep(1)
        PRINT_DBG("Opts: %r : %r" %(len(opts.text), opts.text))

        #if len(items) == 1:
        if len(opts.text) == 0:
            PRINT("Unable to parse %r" % (stock))
            f = open("unparsed_stocks3.txt", "a")
            f.write(stock)
            f.write("\n")
            f.close()
            driver.close()
            return
        if not '\n' in opts.text:
            stock_name = opts.text
            #time.sleep(5)
            elem.send_keys(Keys.RETURN)
            break

        #attr=driver.find_element_by_name('txtStock').get_attribute('innerHTML')
        #attr=elem.get_attribute('innerHTML')
    #elem.send_keys(stock, Keys.ARROW_DOWN)
    #time.sleep(2)
    #elem.send_keys(Keys.RETURN)
    
    #time.sleep(20)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.ID, 'lblCompany')))
    except TimeoutException:
        PRINT("Unable to parse %r" %(stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
        return
    #PRINT_DBG(str(html_src))

    if driver.current_url == old_url:
        PRINT("Unable to parse %r" %(stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        #PRINT_DBG("Found stock %r" %(stock))
        html_src=driver.page_source
        html_file = "html_pages/%s.html" %(stock_name)
        f = open(html_file, "w")
        f.write(html_src)
        f.close()
 
#    try:
#        element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
#        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.ID, 'IdOfMyElement')))
#        element = WebDriverWait(driver, 100).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
#        html_file = "html_pages/%s.html" %(stock)  
#        f = open(html_file, "w")
#        f.write(html_src)
#        f.close()
#    finally:
#        PRINT_DBG("Unable to parse %r" %(stock))
#        f = open("unparsed_stocks.txt", "a")
#        f.write(stock)
#        f.write("\n")
#        f.close()

    driver.close()
    
    #try:
    #    element = WebDriverWait(driver, 100).until(EC.title_contains((By.ID, stock)))
    #finally:
    #    driver.close()
    
    #assert "No results found." not in driver.page_source
    #time.sleep(5)

def get_India_all_stocks_html():
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
#    with open("missing_files.txt") as f:
#        for line in f:
#            line = line.replace("\n","")
#            print(line)
#            get_stock_page(line)

    for i in range(0,sheet.nrows):
    #for i in range(1,10):
        PRINT("%r: %r" %(i, sheet.cell_value(i, 2)))
        get_India_stock_page(sheet.cell_value(i,2))
        
#    f = open('NSE_Stocks.csv')
#    #f = open('BSE_Stocks.csv')
#    csv_f = csv.reader(f)
#    for row in csv_f:
#        PRINT_DBG(row)
#        #PRINT_DBG(row[1])
#        #PRINT_DBG(row[0], row[1], row[2],)

# Get stock split information
def get_stock_split_info_yahoo(stk):
    sym = stk['bscs']['symbol'] + '.BO'
    #get split info from Yahoo Finance
    data = yf(sym).get_key_statistics_data()
    stk['bscs']['split_factor'] = float(Fraction(data[sym]['lastSplitFactor']))
    d = data[sym]['lastSplitDate']
    stk['bscs']['split_date'] = d
    stk['bscs']['split_year'] = datetime.datetime.strptime(d, '%Y-%m-%d').year 

def get_stock_split_info(stk):
    wb = xlrd.open_workbook('India_Stocks/split_data.xls')
    sheet = wb.sheet_by_index(0)
    for i in range(1,sheet.nrows):
        if str(sheet.cell_value(i, 0)) == stk['bscs']['name']:
            stk['bscs']['split_date'] = sheet.cell_value(i,1)
            stk['bscs']['split_year'] = datetime.datetime.strptime(stk['bscs']['split_date'], '%d-%b-%Y').year
            try:
                stk['bscs']['split_factor'] = int(sheet.cell_value(i, 3)) / int(sheet.cell_value(i,4))
            except ZeroDivisionError:
                stk['bscs']['split_factor']=1
            return
    if stk['bscs']['face_value'] != 10:
        PRINT_ERR("Could not find split date for %s, facevalue: %r" %(stk['bscs']['symbol'], stk['bscs']['face_value']))   

# Get symbol name for bse symbol
# Get sector information
def get_symbol_and_sector(stk):
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    #sheet.cell_value(0,0)

    for i in range(1,sheet.nrows):
        if str(int(sheet.cell_value(i, 0))) == stk['bscs']['bse_symbol']:
            stk['bscs']['symbol'] = sheet.cell_value(i,1)
            stk['bscs']['sector'] = sheet.cell_value(i,7)
            return
    PRINT_ERR("Cant find symbol name for %s" %(stk['bscs']['bse_symbol']))


