import json
import xlrd
import xlwt
import urllib, requests
from xlwt import Workbook, Formula
from datetime import timedelta
from datetime import datetime as dt
import time
import pandas as pd
import copy
import math
from math import nan, isnan

from bokeh.io import export_png, export_svgs
from bokeh.models import ColumnDataSource, DataTable, TableColumn

#import matplotlib.pyplot as plt
#import pandas as pd
#from pandas.table.plotting import table

from datastructures import *
import DB
from common import *
import hdf5

def save_df_as_image(df, path):
    source = ColumnDataSource(df)
    #df_columns = [df.index.name]
    #df_columns.extend(df.columns.values)
    #df_columns = [df.columns.values]
    df_columns = list(df.columns)
    columns_for_table=[]
    for column in df_columns:
        columns_for_table.append(TableColumn(field=column, title=column))
    
    data_table = DataTable(source=source, columns=columns_for_table,height_policy="auto",width_policy="auto",index_position=None)
    export_png(data_table, filename = path)

#def save_image(df, filename):
#    ax = plt.subplot(111, frame_on=False) # no visible frame
#    ax.xaxis.set_visible(False)  # hide the x axis
#    ax.yaxis.set_visible(False)  # hide the y axis
#    
#    table(ax, df)  # where df is your data frame
#    
#    plt.savefig(filename)

#def send_telegram_message(message: str,
#                          chat_id: str,
#                          api_key: str,
#                          proxy_username: str = None,
#                          proxy_password: str = None,
#		  proxy_url: str = None):
#    responses = {}
#
#    proxies = None
#    headers = {'Content-Type': 'application/json',
#               'Proxy-Authorization': 'Basic base64'}
#    data_dict = {'chat_id': chat_id,
#                 'text': message,
#                 'parse_mode': 'HTML',
#                 'disable_notification': True}
#    data = json.dumps(data_dict)
#    url = f'https://api.telegram.org/bot{api_key}/sendMessage'
#    response = requests.post(url,
#                             data=data,
#                             headers=headers,
#                             verify=False)
#    return response

def notify_message(message, token='stock_notify'):
    if message is None or message == "":
        return

    time.sleep(1)
    chat_id = get_telegram_chat_id(token=token)
    token = get_telegram_token_id(token=token)

    if len(chat_id) == 0 or len(token) == 0:
        print("Invalid token or chat id for %s", token)
        return

    url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
        token, chat_id, urllib.parse.quote_plus(message))
    resp = requests.get(url, timeout=10)
    #print(resp)
    if resp.status_code != 200:
        print("Failed to send notification with message: %s, err code: %r, err: %r" %(message, resp.status_code, resp.text))
    time.sleep(1)

def get_instrument_from_db(sym, db_client):
    if sym is None or sym == "":
        print("Error: Symbol is empty, pass one")
        return None, None

    if db_client is None:
        print("Error: db_client is empty, pass one")
        return None, None

    db = db_client['Stocks']
    stocks = db.US_Stocks
    db = db_client['Cryptos']
    cryptos = db.Cryptos
    #db = db_client['ETFs']
    #Etfs = db.ETFs

    stks = stocks.find({'bscs.symbol':sym})
    crypts = cryptos.find({'bscs.symbol':sym})
    #etfs = Etfs.find({'bscs.symbol':sym})
    if stks.count() != 0:
        instrument = stks[0]
        instruments = stocks
    elif cryptos.count() != 0:
        instrument = crypts[0]
        instruments = cryptos
    #elif etfs.count() != 0:
    #    instrument = etfs[0]
    #    instruments = Etfs
    else:
        print("Instrument: %s doesn't exist" %(sym))
        return None, None
    return instrument, instruments

def get_instrument(sym, db_client):
    instrument, instruments = get_instrument_from_db(sym, db_client)
    if instrument is None:
        return None

    try:
        if instrument['dates']['mysql_price_pull_success'] != True:
            return None
        if instrument['dates']['mysql_price_date'] != DB.get_latest_trading_day():
            return None
        if instrument['price_change']['date'] != DB.get_latest_trading_day():
            return None
        if instrument['technicals']['date'] != DB.get_latest_trading_day():
            return None
    except Exception as e:
        print("symbol: %s error" %(sym))
        return None

    str = 'Symbol: '+ instrument['bscs']['symbol']
    if 'General' in instrument.keys():
        if instrument['General']['Exchange'] not in major_exchanges:
            if 'tracking' not in instrument['bscs'].keys() or \
                    instrument['bscs']['tracking'] is False: 
                instrument['bscs']['tracking']=True
                DB.add_all_stock_data(instrument)
                DB.update_field(instruments, instrument['bscs']['symbol'], 'bscs.tracking', True)
                instrument, instruments = get_instrument_from_db(sym, db_client)
                if instrument is None:
                    return None

        if 'Code' in instrument['General'].keys():
            str = str + ' Name: ' + instrument['General']['Code']
        elif 'Name' in instrument['General'].keys():
            str = str + ' Name: ' + instrument['General']['Name'] +' '
        if 'Type' in instrument['General'].keys():
            str = str + " " + instrument['General']['Type']
    print(str)

    return instrument

def min_rsi(instrument):
    if instrument is None:
        return
    
    sym = instrument['bscs']['symbol']
    if 'technicals' in instrument.keys() and 'rsi' in instrument['technicals'].keys() and 'sar' in instrument['technicals'].keys():
        min_rsi = instrument['technicals']['rsi']['latest'] - instrument['technicals']['rsi']['60day_min']
        if min_rsi <= 5:
            message = sym + " : min_rsi: "+ str(min_rsi) + "\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def max_rsi(instrument):
    if instrument is None:
        return
    
    sym = instrument['bscs']['symbol']
    if 'technicals' in instrument.keys() and 'rsi' in instrument['technicals'].keys() and 'sar' in instrument['technicals'].keys():
        max_rsi = instrument['technicals']['rsi']['60day_max'] - instrument['technicals']['rsi']['latest']
        if max_rsi <= 5:
            message = sym + " : max_rsi: "+ str(max_rsi) + "\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def max_rsi_price(instrument):
    if instrument is None:
        return
    
    sym = instrument['bscs']['symbol']
    if 'technicals' in instrument.keys() and 'rsi' in instrument['technicals'].keys() and 'cur_price_max_rsi_change' in instrument['technicals']['rsi'].keys() and 'sar' in instrument['technicals'].keys():
        cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
        if cur_price_max_rsi_change >= 20: #greater than 20%
            message = sym + " : cur_price_max_rsi_change: "+ str(cur_price_max_rsi_change) + "%\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def uptrend(instrument):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']
    if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        trend = instrument['technicals']['sar']['ta_psar_trend']
        if trend > 0 and trend <= 1:
        #if trend > 0 and trend <= 3:
            cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
            pre_trend_pri_chg = instrument['technicals']['sar']['ta_psar_prev_trend_price_change'] * 100
            # Look only for companies with previous trend losing morethan 10 percent
            if pre_trend_pri_chg >= -10:
                return
            message = sym + ":" +instrument['General']['Name'] +"\n" +\
                    "uptrend: "+ str(trend) + "L\n" + \
                    "price: $"+ str(instrument['price_change']['price']) + "\n" +\
                    "day change: "+ str(round(instrument['price_change']['day']*100,2)) +"%" + "\n" +\
                    "cur_price_max_rsi_change: "+ str(cur_price_max_rsi_change) + "%\n" +\
                    "trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence'] + "\n" +\
                    "Mcap:" + str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
            notify_message(message)

def downtrend(instrument):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']
    if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        trend = instrument['technicals']['sar']['ta_psar_trend']
        #if trend < 0 and trend >= -3:
        if trend == -1:
            cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
            message = sym + " : downtrend: "+ str(trend) + "S\n" +\
                    "price: $"+ str(instrument['price_change']['price']) + "\n" +\
                    "cur_price_max_rsi_change: "+ str(cur_price_max_rsi_change) + "%\n" +\
                    "trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence'] +"\n" +\
                    "Mcap:" + str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
            notify_message(message)

def price_change_day(instrument):
    if instrument is None:
        return

    Mn = 1000000
    Bn = 1000*Mn
    Tn = 1000*Bn

    if 'Highlights' not in instrument.keys() or \
            'MarketCaptalization' not in instrument['Highlights'].keys() or \
            instrument['Highlights']['MarketCapitalization'] is None:
                return

    if instrument['Highlights']['MarketCapitalization'] > 100 * Bn:
        up = 4.5
        down = -4.5
    elif instrument['Highlights']['MarketCapitalization'] > 50 * Bn:
        up = 5
        down = -5
    elif instrument['Highlights']['MarketCapitalization'] > 25 * Bn:
        up = 10
        down = -10
    elif instrument['Highlights']['MarketCapitalization'] > 1 * Bn:
        up = 10
        down = -10
    elif instrument['Highlights']['MarketCapitalization'] > 500 * Mn:
        up = 15
        down = -15
    else:
        up = 40
        down = -40
    
    sym = instrument['bscs']['symbol']
    if 'price_change' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        change = round(instrument['price_change']['day'] * 100,2)
        if change <= down or change >= up:
            print(change)
            message = sym + ": " + instrument['General']['Name'] +"\n" +\
                    "price_change_day: "+ str(change) + "%\n" +\
                    "price: $"+ str(instrument['price_change']['price']) + "\n" +\
                    "trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence'] +"\n" +\
                    "Mcap:" + str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
            notify_message(message)

def price_change_week(instrument):
    if instrument is None:
        return

    Mn = 1000000
    Bn = 1000*Mn
    Tn = 1000*Bn

    if instrument['Highlights']['MarketCapitalization'] > 100 * Bn:
        up = 7
        down = -7
    elif instrument['Highlights']['MarketCapitalization'] > 50 * Bn:
        up = 10
        down = -10
    elif instrument['Highlights']['MarketCapitalization'] > 25 * Bn:
        up = 15
        down = -15
    elif instrument['Highlights']['MarketCapitalization'] > 1 * Bn:
        up = 20
        down = -20
    elif instrument['Highlights']['MarketCapitalization'] > 500 * Mn:
        up = 30
        down = -30
    else:
        up = 80
        down = -80
 
    sym = instrument['bscs']['symbol']
    if 'price_change' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        change = instrument['price_change']['week'] * 100
        if change <= down or change >= up:
            message = sym + ":" + instrument['General']['Name'] +"\n" +\
                    "price_change_week: "+ str(change) + "%\n" +\
                    "price: $"+ str(instrument['price_change']['price']) + "\n" +\
                    "trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence'] +"\n" +\
                    "Mcap:" + str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000),2) + "Bn"
            notify_message(message)

earnings_stks = []
def earnings_date(instrument, radar_syms=None):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']

    #if radar_syms is None:
    #    radar_syms = DB.get_radar_symbols()

    #if sym not in radar_syms:
    #    return
    if sym in earnings_stks:
        return
    if 'dates' in instrument.keys() and 'last_earnings_report_date' in instrument['dates'].keys():
            earning_date = instrument['dates']['last_earnings_report_date'].date()
            # If earnings is tomorrow, send a notification
            if earning_date == dt.now().date() + timedelta(1) or earning_date == DB.get_next_trading_day():
                if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
                    print("Earnings date for %s: %s" %(sym, earning_date))
                    time.sleep(3)
                    message = sym + ":" + instrument['General']['Name'] + "\n" +\
                            "earnings_date: "+ str(earning_date) #+ "\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
                    notify_message(message)
                    earnings_stks.append(sym)
                else:
                    message = sym +" technicals not available"
                    notify_message(message)

# Earnings with in a week
def week_earnings_date():
    wb = xlrd.open_workbook(radar_stocks_file)
    if wb.nsheets < 1:
        print("No sheets found")
        return

    week_df = pd.DataFrame(columns=['Sym','Name'])
    fields = {
                    'Name':'',
                    'Trend':int(),
                    'Price': float(), 
                    'Day_Change': float(),
                    'Avg_Vol_X_Price_Mn': float(),
                    'Cur_Price_Max_Rsi_Change': float(),
                    'Trend_Sequence':'',
                    'Trend_Sequence_Change':'',
                    'Prev_Trend_Change':float(),
                    'Days_To_Earnings':'',
                    'MCap':float()
                }
    uptrend_df = pd.DataFrame(fields, index=[])

    week_earnings_stks = {}
    tomorrow_earnings_stks = {}
    db_client = DB.open_db_client()

    try:
        for j in range(1,wb.nsheets):
            entries = []
            sheet = wb.sheet_by_index(j)
            #for i in range(1,3):
            for i in range(1,sheet.nrows):
                entry = []
                sym  = str(sheet.cell_value(i, 0))
                if sym == '' or sym is None:
                    continue
                name = str(sheet.cell_value(i, 1))
                instrument = get_instrument(sym, db_client)
                if instrument == None:
                    continue

                # Earnings dates
                if 'dates' in instrument.keys() and 'last_earnings_report_date' in instrument['dates'].keys():
                        edate = instrument['dates']['last_earnings_report_date'].date()
                        if edate > dt.now().date() and edate <= dt.now().date() + timedelta(6):
                            if sym not in week_earnings_stks.keys():
                                week_earnings_stks[str(edate)] = instrument['General']['Name']
                                week_df.loc[str(edate)] = [sym, instrument['General']['Name']]
                        # If earnings is tomorrow, send a notification
                        if edate == dt.now().date() + timedelta(1) or edate == DB.get_next_trading_day():
                            if sym not in tomorrow_earnings_stks.keys():
                                tomorrow_earnings_stks[sym] = instrument['General']['Name']
                # Uptrend
                if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
                    trend = instrument['technicals']['sar']['ta_psar_trend']
                    if sym not in uptrend_df.index:
                        if trend > 0 and trend <= 1:
                        #if trend > 0 and trend <= 3:
                            cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
                            pre_trend_pri_chg = instrument['technicals']['sar']['ta_psar_prev_trend_price_change']

                            earnings_date = instrument['dates']['last_earnings_report_date'].date()
                            today = dt.combine(dt.now(), dt.min.time()).date()
                            days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                            days = int(days)

                            uptrend_df.loc[sym] = [
                                                    instrument['General']['Name'], 
                                                    trend, 
                                                    round(instrument['price_change']['price'],2),
                                                    round(instrument['price_change']['day']*100,2),
                                                    round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                                                    cur_price_max_rsi_change,
                                                    str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                                                    str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                                                    round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change'],2),
                                                    str(days),
                                                    round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                                                    #str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
                                                    ]

        if len(week_df) > 0:
            message = "Earnings in 7 days\n"
            for index, d in week_df.iterrows():
                s = d['Sym'] + ":" + d['Name'] + "\n" +\
                    "earnings_date: "+ str(index) +"\n\n"
                message = message + s
            notify_message(message, token='earnings_dates')

        if len(tomorrow_earnings_stks) > 0:
            message = "Earnings Tomorrow\n"
            for sym, name in tomorrow_earnings_stks.items():
                s = sym + ":" + name + "\n"
                message = message + s
            notify_message(message, token='earnings_dates')

        if len(uptrend_df) > 0:
            message = "Radar Stocks Uptrend:\n=====================\n"
            for index,d in uptrend_df.iterrows():
                s = str(index) + ":" +d['Name'] +"\n" +\
                        "trend: "
                if d['Trend'] > 0:
                    s = s + str(d['Trend']) + "L\n"
                else:
                    s = s + str(abs(d['Trend'])) + "S\n"
                s = s + "price: $"+ str(d['Price']) + "\n" +\
                    "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
                    "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
                    "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
                    "trend: " + d['Trend_Sequence'] + "\n" +\
                    "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
                    "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
                    "Days_To_Earnings: " + d['Days_To_Earnings'] +"\n" +\
                    "Mcap: $" + str(d['MCap']) + "Bn\n\n"

                message = message + s
            notify_message(message, token='radar_stocks')

    finally:
        DB.close_db_client(db_client)

def notify_radar_stocks(country='US'):
    if country != 'US':
        return

    wb = xlrd.open_workbook(radar_stocks_file)
    if wb.nsheets < 1:
        print("No sheets found")
        return

    db_client = DB.open_db_client()

    try:
        #week_earnings_date()
        for call in calls.values():
            for j in range(1,wb.nsheets):
                entries = []
                sheet = wb.sheet_by_index(j)
                #for i in range(1,3):
                for i in range(1,sheet.nrows):
                    entry = []
                    sym  = str(sheet.cell_value(i, 0))
                    if sym == '' or sym is None:
                        continue
                    name = str(sheet.cell_value(i, 1))
                    instrument = get_instrument(sym, db_client)
                    if instrument == None:
                        continue
                    call(instrument)
                    #for call in calls.values():
                    #    call(instrument)

    finally:
        DB.close_db_client(db_client)

def notify_all_stocks():
    c  = DB.open_db_client()
    db = c['Stocks']

    stocks = db.US_Stocks.find({"$and":[\
                                            {"$or": [\
                                                        {'General.Exchange':{"$in":major_exchanges}},\
                                                        {"$and": [ \
                                                                    {'General.Exchange':{"$nin":major_exchanges}},\
                                                                    {'bscs.tracking':{'$exists':True}}, \
                                                                ] \
                                                        },\
                                                    ]\
                                            },\
                                            {'General.Type':'Common Stock'},\
                                            {'General.IsDelisted': False},\
                                            {'Highlights.MarketCapitalizationMln': {"$gte":1000}},\
                                            {"$and": [ \
                                                        #{'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
                                                        {'dates.mysql_price_pull_success': True},\
                                                        {'failcount.mysql_price_failcount': {'$eq': 0}},\
                                                        #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                                                    ]\
                                            }, \
                                            #{"$or":[\
                                            #        {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
                                            #        {'price_change.date': {"$exists": False}}\
                                            #        ]\
                                            #},\
                                        ]}).batch_size(10)
    #stocks = db.US_Stocks.find({"bscs.symbol":"PLTR"})
    print("stocks: %d" %(stocks.count()))

    fields = {
                    'Name':'',
                    'Trend':int(),
                    'Price': float(), 
                    'Day_Change': float(), 
                    'Cur_Price_Max_Rsi_Change': float(),
                    'Trend_Sequence':'',
                    'Trend_Sequence_Change':'',
                    'Prev_Trend_Change':float(),
                    'MCap':float()
                }
    uptrend_df = pd.DataFrame(fields, index=[])
    mstar_df = pd.DataFrame(fields, index=[])

    options_fields = {
                    'Name':'',
                    'Price': float(), 
                    'Premium': '',
                    'AllPremium': '',
                    'StrikePrice': float(),
                    'Bid':'',
                    'Ask':'',
                    'Mid':'',
                    'DTE':'',
                    'MCap':float()
                }
    options_df = pd.DataFrame(fields, index=[])

    #for i, stk in enumerate(stocks):
    #        print("%d: %s: %s" %(i, stk['bscs']['symbol'], stk['General']['Name']))
    #        #for call in calls.values():
    #        #    call(stk)
    #        uptrend(stk)
    for i, stk in enumerate(stocks):
            #price_change_day(stk)
            df = get_uptrend(stk)
            if len(df) > 0:
                uptrend_df = pd.concat([uptrend_df, df])
            df = get_mstar(stk)
            if len(df) > 0:
                mstar_df = pd.concat([mstar_df, df])
            df = get_option(stk)
            if len(df) > 0:
                option_df = pd.concat([option_df, df])
    #for i, stk in enumerate(stocks):
    #        price_change_week(stk)

    #send_uptrend_message(uptrend_df)
    send_mstar_message(mstar_df)
    send_options_message(option_df)

    DB.close_db_client(c)

def get_ratings(fwh=False, purebuy=False):
    fields = {
                    'Name':'',
                    'Rating': int(),
                    'Target Price': float(),
                    'WallSt Target Price': float(),
                    'Strong Buy': int(),
                    'Buy': int(),
                    'Hold': int(),
                    'Sell': int(),
                    'Strong Sell': int(),
                    'Price': float(), 
                    'StrikePrice': float(),
                    'Expiry':'',
                    'EarningsDate':'',
                    'Premium': float(),
                    'AllPremium': float(),
                    'Bid':'',
                    'Mid':'',
                    'Ask':'',
                    'DTE':int(),
                    'DaysToEarnings': int(),
                    'MCap':float()
                }

    df = pd.DataFrame(fields, index=[])

    c  = DB.open_db_client()
    db = c['Stocks']

    Mn = 1000000
    Bn = 1000*Mn

    conditions = [ \
                    {"General.IsDelisted": False},\
                    {'General.Type':'Common Stock'},\
                    {"$or": [\
                                {'General.Exchange':{"$in":major_exchanges}},\
                                {"$and": [ \
                                            {'General.Exchange':{"$nin":major_exchanges}},\
                                            {'bscs.tracking':{'$exists':True}}, \
                                        ] \
                                },\
                            ]\
                    },\
                    #{'Highlights.MarketCapitalization':{'$gte':5 * Bn}},\
                    #{'dates.technicals_pull_date': {'$gte':DB.get_latest_trading_day()}}\
                ]
    if fwh is True:
        conditions.append({'Highlights.MarketCapitalization':{'$gte':5 * Bn}})
    else:
        conditions.append({'Highlights.MarketCapitalization':{'$gte':5 * Bn}})
 
    # Get top 10 stocks with StrongBuy rating
    if fwh is True:
        stocks = db.US_Stocks.find({'$and':conditions}).sort([["price_change.with_52week_high", 1]]).allow_disk_use(True).sort([["price_change.year", -1]]).allow_disk_use(True).limit(100)
    else:
        #stocks = db.US_Stocks.find({'$and':conditions}).sort([["AnalystRatings.Rating", -1]]).allow_disk_use(True).limit(100)
        stocks = db.US_Stocks.find({'$and':conditions}).sort([["AnalystRatings.StrongBuy", -1]]).allow_disk_use(True).limit(100)

    print("Strong Buy stocks: %d" %(stocks.count()))

    td = dt.now()
    try:
        for i, instrument in enumerate(stocks):
            if i > 100:
                break
            try:
                earnings_date = instrument['dates']['last_earnings_report_date'].date()
                today = dt.combine(dt.now(), dt.min.time()).date()
                days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                days_to_earnings = int(days)

                df.at[instrument['bscs']['symbol'], 'Name'] = instrument['General']['Name']

                df.at[instrument['bscs']['symbol'],'total_dates'] = instrument['price_change']['total_dates']
                df.at[instrument['bscs']['symbol'],'ten_percent_down_times'] = instrument['price_change']['ten_percent_chg_times']
                df.at[instrument['bscs']['symbol'],'twenty_percent_down_times'] = instrument['price_change']['twenty_percent_chg_times']
                if 'AnalystRatings' in instrument.keys():
                    df.at[instrument['bscs']['symbol'],'Rating'] = instrument['AnalystRatings']['Rating']
                    df.at[instrument['bscs']['symbol'],'Target Price'] = instrument['AnalystRatings']['TargetPrice']
                    df.at[instrument['bscs']['symbol'],'WallSt Target Price'] = instrument['Highlights']['WallStreetTargetPrice']
                    df.at[instrument['bscs']['symbol'],'Strong Buy'] = instrument['AnalystRatings']['StrongBuy']
                    df.at[instrument['bscs']['symbol'],'Buy'] = instrument['AnalystRatings']['Buy']
                    df.at[instrument['bscs']['symbol'],'Hold'] = instrument['AnalystRatings']['Hold']
                    df.at[instrument['bscs']['symbol'],'Sell'] = instrument['AnalystRatings']['Sell']
                    df.at[instrument['bscs']['symbol'],'Strong Sell'] = instrument['AnalystRatings']['StrongSell']
                df.at[instrument['bscs']['symbol'], 'Price'] = instrument['options_data']['price']
                df.at[instrument['bscs']['symbol'], 'StrikePrice'] = instrument['options_data']['strike_price']
                if isinstance(instrument['options_data']['expiration'], td.__class__):
                    df.at[instrument['bscs']['symbol'], 'Expiry'] = str(instrument['options_data']['expiration'].date())
                df.at[instrument['bscs']['symbol'], 'EarningsDate'] = str(earnings_date)
                df.at[instrument['bscs']['symbol'], 'Premium'] = round(instrument['options_data']['mid_pr'],2)
                df.at[instrument['bscs']['symbol'], 'AllPremium'] = round(instrument['options_data']['all_pr'],2)
                df.at[instrument['bscs']['symbol'], 'Bid'] = '$'+str(instrument['options_data']['bid'])
                df.at[instrument['bscs']['symbol'], 'Mid'] = '$'+str(instrument['options_data']['mid'])
                df.at[instrument['bscs']['symbol'], 'Ask'] = '$'+str(instrument['options_data']['ask'])
                if 'risk_percent' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'],'risk_percent'] = instrument['options_data']['risk_percent']
                if 'twenty_percent_down' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'],'twenty_percent_down'] = instrument['options_data']['twenty_percent_down']
                if 'dte' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'], 'DTE'] = instrument['options_data']['dte']
                df.at[instrument['bscs']['symbol'], 'DaysToEarnings'] = days_to_earnings
                df.at[instrument['bscs']['symbol'], 'MCap'] = round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                if fwh:
                    df.at[instrument['bscs']['symbol'], 'YearChange'] = instrument['price_change']["year"]

            except Exception as E:
                print("Ratings: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
                continue
    
    except Exception as E:
        print("GetRatings: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

    df = df.dropna()
    if len(df) == 0:
        return

    df = df.loc[df['DTE'] < 10]

    if fwh is True: 
        df = df.iloc[0:20]
    elif purebuy is True:
        df = df.iloc[0:10]
    else:
        df = df.sort_values(by=['Premium'], ascending=False)
        df = df.iloc[0:20]
    count=7
    l = len(df)
    iters = math.ceil(l/count)# + 1
    #df = df.iloc[0:20]

    st = 0
    en = count
    for i in range(iters):
        message = str(i+1) +": Strong Buy Stocks:\n=====================\n"
        sdf = df.iloc[st:en]
        if len(sdf) == 0:
            break
 
        for index,d in sdf.iterrows():
            s = str(index) + ":" +d['Name'] +"\n" +\
                    "Rating: " + str(d['Rating']) + "\n" +\
                    "Target Price: $" + str(d['Target Price']) + "\n" +\
                    "WallSt Target Price: $" + str(d['WallSt Target Price']) + "\n" +\
                    "Strong Buy: " + str(d['Strong Buy']) + "\n" +\
                    "Buy: " + str(d['Buy']) + "\n" +\
                    "Hold: " + str(d['Hold']) + "\n" +\
                    "Sell: " + str(d['Sell']) + "\n" +\
                    "Strong Sell: " + str(d['Strong Sell']) + "\n" +\
                    "price: $"+ str(d['Price']) + "\n" +\
                    "strike_price: "+ str(d['StrikePrice']) + "\n" +\
                    "expiration: "+ d['Expiry'] + "\n" +\
                    "earnings_date: "+ d['EarningsDate'] + "\n" +\
                    "10_pcnt_down_times: " + str(int(d['ten_percent_down_times'])) + "/" + str(int(d['total_dates'])) + "\n" +\
                    "20_pcnt_down_times: " + str(int(d['twenty_percent_down_times'])) + "/" + str(int(d['total_dates'])) + "\n" +\
                    "premium: " + str(d['Premium']) + "%\n" +\
                    "price+premium: " + str(d['AllPremium']) + "%\n" +\
                    "bid: " + d['Bid'] + "\n" +\
                    "mid: " + d['Mid'] + "\n" +\
                    "ask: " + d['Ask'] + "\n" +\
                    "Risk Percent: " + str(d['risk_percent']) + "%\n" +\
                    "TwentyPercentDown: " + str(d['twenty_percent_down']) + "%\n" +\
                    "dte: " + str(d['DTE']) + " days\n" +\
                    "days_to_earnings: " + str(d['DaysToEarnings']) + " days\n" +\
                    "Mcap: $" + str(d['MCap']) + "Bn\n"
            if fwh:
                s = s + "YearChange: " + str(round(d['YearChange']*100,2)) + "%\n"

            s = s + "\n"

            message = message + s

        if purebuy:
            notify_message(message, token='strong_buy_pure')
        elif fwh:
            notify_message(message, token='fwh')
        else:
            notify_message(message, token='strong_buy')
        st = en
        en = en + count

    if purebuy:
        return
    # Get top 10 stocks with StrongSell rating
    stks = db.US_Stocks.find({'$and':conditions}).sort([["AnalystRatings.StrongSell", -1]]).allow_disk_use(True).limit(30)

    print("Strong Sell stocks: %d" %(stks.count()))

    df = pd.DataFrame()
    try:
        for i, instrument in enumerate(stks):
            if i > 30:
                break
            if instrument['bscs']['symbol'] == 'MTD':
                print("MTD")
            try:
                earnings_date = instrument['dates']['last_earnings_report_date'].date()
                today = dt.combine(dt.now(), dt.min.time()).date()
                days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                days_to_earnings = int(days)

                df.at[instrument['bscs']['symbol'], 'Name'] = instrument['General']['Name']
                df.at[instrument['bscs']['symbol'],'Rating'] = instrument['AnalystRatings']['Rating']
                df.at[instrument['bscs']['symbol'],'Target Price'] = instrument['AnalystRatings']['TargetPrice']
                df.at[instrument['bscs']['symbol'],'WallSt Target Price'] = instrument['Highlights']['WallStreetTargetPrice']
                df.at[instrument['bscs']['symbol'],'Strong Buy'] = instrument['AnalystRatings']['StrongBuy']
                df.at[instrument['bscs']['symbol'],'Buy'] = instrument['AnalystRatings']['Buy']
                df.at[instrument['bscs']['symbol'],'Hold'] = instrument['AnalystRatings']['Hold']
                df.at[instrument['bscs']['symbol'],'Sell'] = instrument['AnalystRatings']['Sell']
                df.at[instrument['bscs']['symbol'],'Strong Sell'] = instrument['AnalystRatings']['StrongSell']
                df.at[instrument['bscs']['symbol'], 'Price'] = instrument['options_data']['price']
                df.at[instrument['bscs']['symbol'], 'StrikePrice'] = instrument['options_data']['strike_price']
                if isinstance(instrument['options_data']['expiration'], td.__class__):
                    df.at[instrument['bscs']['symbol'], 'Expiry'] = str(instrument['options_data']['expiration'].date())
                df.at[instrument['bscs']['symbol'], 'EarningsDate'] = str(earnings_date)
                df.at[instrument['bscs']['symbol'], 'Premium'] = round(instrument['options_data']['mid_pr'],2)
                df.at[instrument['bscs']['symbol'], 'AllPremium'] = round(instrument['options_data']['all_pr'],2)
                df.at[instrument['bscs']['symbol'], 'Bid'] = '$'+str(instrument['options_data']['bid'])
                df.at[instrument['bscs']['symbol'], 'Mid'] = '$'+str(instrument['options_data']['mid'])
                df.at[instrument['bscs']['symbol'], 'Ask'] = '$'+str(instrument['options_data']['ask'])
                if 'risk_percent' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'],'risk_percent'] = instrument['options_data']['risk_percent']
                if 'twenty_percent_down' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'],'twenty_percent_down'] = instrument['options_data']['twenty_percent_down']
                if 'dte' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'], 'DTE'] = instrument['options_data']['dte']
 
                df.at[instrument['bscs']['symbol'], 'DaysToEarnings'] = days_to_earnings
                df.at[instrument['bscs']['symbol'], 'MCap'] = round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)

            except Exception as E:
                print("Options: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    
    except Exception as E:
        print("Options: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

    if len(df) == 0:
        return

    #df = df.sort_values(by=['Premium'], ascending=False)
    df = df.iloc[0:20]
    count=7
    l = len(df)
    iters = math.ceil(l/count)# + 1
    #df = df.iloc[0:20]

    st = 0
    en = count
    for i in range(iters):
        message = str(i+1) +": Strong Sell Stocks:\n=====================\n"
        sdf = df.iloc[st:en]
        if len(sdf) == 0:
            break
 
        for index,d in sdf.iterrows():
            s = str(index) + ":" +d['Name'] +"\n" +\
                "Rating: " + str(d['Rating']) + "\n" +\
                "Target Price: $" + str(d['Target Price']) + "\n" +\
                "WallSt Target Price: $" + str(d['WallSt Target Price']) + "\n" +\
                "Strong Buy: " + str(d['Strong Buy']) + "\n" +\
                "Buy: " + str(d['Buy']) + "\n" +\
                "Hold: " + str(d['Hold']) + "\n" +\
                "Sell: " + str(d['Sell']) + "\n" +\
                "Strong Sell: " + str(d['Strong Sell']) + "\n" +\
                "price: $"+ str(d['Price']) + "\n" +\
                "strike_price: "+ str(d['StrikePrice']) + "\n" +\
                "expiration: "+ str(d['Expiry']) + "\n" +\
                "earnings_date: "+ str(d['EarningsDate']) + "\n" +\
                "premium: " + str(d['Premium']) + "%\n" +\
                "price+premium: " + str(d['AllPremium']) + "%\n" +\
                "bid: " + str(d['Bid']) + "\n" +\
                "mid: " + str(d['Mid']) + "\n" +\
                "ask: " + str(d['Ask']) + "\n" +\
                "Risk Percent: " + str(d['risk_percent']) + "%\n" +\
                "TwentyPercentDown: " + str(d['twenty_percent_down']) + "%\n" +\
                "dte: " + str(d['DTE']) + " days\n" +\
                "days_to_earnings: " + str(d['DaysToEarnings']) + " days\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n"

            s = s + "\n"

            message = message + s

        notify_message(message, token='strong_sell')
        st = en
        en = en + count

def get_options(grp):
    fields = {
                    'Name':'',
                    'Price': float(), 
                    'StrikePrice': float(),
                    'Expiry':'',
                    'EarningsDate':'',
                    'Premium': float(),
                    'AllPremium': float(),
                    'Bid':'',
                    'Mid':'',
                    'Ask':'',
                    'DTE':int(),
                    'DaysToEarnings': int(),
                    'MCap':float()
                }
    if grp == 'options2':
        fields2 = {
                        'Rating': int(),
                        'Target Price': float(),
                        'WallSt Target Price': float(),
                        'Strong Buy': int(),
                        'Buy': int(),
                        'Hold': int(),
                        'Sell': int(),
                        'Strong Sell': int(),
                    }
        #fields.update(fields2)
        fields = {**fields, **fields2}

    options_df = pd.DataFrame(fields, index=[])

    c  = DB.open_db_client()
    db = c['Stocks']

    Mn = 1000000
    Bn = 1000*Mn

    #stocks = db.US_Stocks.find({"$and" : [ \
    #                                        {"General.IsDelisted": False},\
    #                                        {'General.Type':'Common Stock'},\
    #                                        {"$or": [\
    #                                                    {'General.Exchange':{"$in":major_exchanges}},\
    #                                                    {"$and": [ \
    #                                                                {'General.Exchange':{"$nin":major_exchanges}},\
    #                                                                {'bscs.tracking':{'$exists':True}}, \
    #                                                            ] \
    #                                                    },\
    #                                                ]\
    #                                        },\
    #                                        {"dates.options_pull_date": {"$eq": DB.get_latest_trading_day()}},\
    #                                        {'options_data.mid_pr' :{'$gte':3}},\
    #                                        {'Highlights.MarketCapitalization': {'$gte': 5 * Bn}},\
    #                                        #{'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}}\
    #                                    ]\
    #                            }\
    #                            )#.batch_size(10).sort([["options_data.mid_pr",1]]).allow_disk_use(True)#.sort([["sno",sort]]).allow_disk_use(True)
    conditions = [ \
                    {"General.IsDelisted": False},\
                    {'General.Type':'Common Stock'},\
                    {"$or": [\
                                {'General.Exchange':{"$in":major_exchanges}},\
                                {"$and": [ \
                                            {'General.Exchange':{"$nin":major_exchanges}},\
                                            {'bscs.tracking':{'$exists':True}}, \
                                        ] \
                                },\
                            ]\
                    },\
                    {"dates.options_pull_date": {"$gte": DB.get_latest_trading_day()}},\
                    {'options_data.mid_pr' :{'$gte':3}},\
                    #{'dates.technicals_pull_date': {'$gte':get_latest_trading_day()}}\
                ]
    if grp == 'options2':
        conditions.append({'Highlights.MarketCapitalization':{'$gte':5 * Bn}})
    else:
        conditions.append({'Highlights.MarketCapitalization':{'$gte':5 * Bn}})
 
    stocks = db.US_Stocks.find({'$and':conditions})
    print("options stocks: %d" %(stocks.count()))

    token = 'dHVKZE1BOFltVVEwLWhsdF9scC15N2h5X1NaVjF6Yldtdnlzd21mTV85ND0'
    headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer '+token
            }

    try:
        for i, instrument in enumerate(stocks):
            if 'options_data' in instrument.keys():
                if instrument['options_data']['strike_price'] < instrument['options_data']['price']:
                    print("Symbol %s price is less than strike price" %(instrument['bscs']['symbol']))
                    pretty_print(instrument['options_data'])
                    continue
                if instrument['options_data']['bid'] == 0:
                    #print("Symbol %s bid price is zero" %(instrument['bscs']['symbol']))
                    #pretty_print(instrument['options_data'])
                    continue

                if instrument['options_data']['dte'] > 10:
                    continue

                # For smaller market caps, expect atleast 4% premium
                if instrument['Highlights']['MarketCapitalization'] < 20 * Bn and instrument['options_data']['mid_pr'] < 4:
                    continue
                        
                if 'earnings_pull_date' not in instrument['options_data'].keys() or \
                    instrument['options_data']['earnings_pull_date'] < DB.get_latest_trading_day():

                    url='https://api.marketdata.app/v1/stocks/earnings/'+instrument['bscs']['symbol']+'/'
                    today = dt.now().date()
                    frm = str(today - timedelta(today.weekday()))
                    #to = str(today + timedelta(4 - today.weekday()))

                    if today.weekday() >= 4:
                        #to = (7 - (today.weekday() + 1)) + 5
                        to = str(today + timedelta((7 - (today.weekday() + 1)) + 5))
                    else:
                        # 0-Mon,1-Tue,2-Wed,3-Thu,4-Fri,5-Sat,6-Sun
                        #to = 4 - today.weekday()
                        to = str(today + timedelta(4 - today.weekday()))
 
                    url = url + '?from=' + frm + '&to=' + to 
                    ret = requests.get(url, headers=headers)
                    if ret.status_code > 203:
                        print("Failed to get earnings data for %r, error code: %r, error: %r" %(instrument['bscs']['symbol'], ret.status_code, ret.text))
                    else:
                        edf=pd.DataFrame(ret.json())
                        if len(edf) > 0 and edf.iloc[0]['reportDate'] != None:
                            try:
                                earnings_date = pd.to_datetime(edf.iloc[0]['reportDate'],unit='s')
                                earnings_date = dt.combine(earnings_date.to_pydatetime(), dt.min.time())
                            except:
                                pass
                        instrument['options_data']['earnings_report_date'] = earnings_date
                        DB.update_field(db.US_Stocks, instrument['bscs']['symbol'], 'options_data.earnings_report_date', earnings_date)

                    instrument['options_data']['earnings_pull_date'] = dt.combine(dt.now(), dt.min.time())
                    DB.update_field(db.US_Stocks, instrument['bscs']['symbol'], 'options_data.earnings_pull_date', instrument['options_data']['earnings_pull_date'])


                bid = instrument['options_data']['bid']
                ask = instrument['options_data']['ask']
                percent_diff = ((ask-bid)/bid) * 100
                if percent_diff > 200:
                    continue

                td = dt.now()
                days_to_earnings = nan
                earnings_date = nan
                if 'earnings_report_date' in instrument['options_data'].keys() and isinstance(instrument['options_data']['earnings_report_date'], td.__class__):
                    earnings_date = instrument['options_data']['earnings_report_date'].date()
                    today = dt.combine(dt.now(), dt.min.time()).date()
                    #days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                    days = (earnings_date - today).days
                    days_to_earnings = int(days)

                    # If earnings is in the same week, ignore that stock
                    #if days_to_earnings >= 0 and \
                    #        days_to_earnings <= instrument['options_data']['dte']:
                    #    continue

                    if days_to_earnings < -90:
                        continue
                #else:
                #    earnings_date = instrument['dates']['last_earnings_report_date'].date()

                #options_df.loc[instrument['bscs']['symbol']] = [
                #                        instrument['General']['Name'], 
                #                        round(instrument['options_data']['price'],2),
                #                        str(instrument['options_data']['strike_price']),
                #                        str(instrument['options_data']['expiration'].date()),
                #                        str(earnings_date),
                #                        round(instrument['options_data']['mid_pr'],2),
                #                        round(instrument['options_data']['all_pr'],2),
                #                        '$'+str(instrument['options_data']['bid']),
                #                        '$'+str(instrument['options_data']['mid']),
                #                        '$'+str(instrument['options_data']['ask']),
                #                        instrument['options_data']['dte'],
                #                        days_to_earnings,
                #                        round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                #                        ]
                #
                try:
                    options_df.at[instrument['bscs']['symbol'], 'Name'] = instrument['General']['Name']
                    options_df.at[instrument['bscs']['symbol'], 'Price'] = instrument['options_data']['price']
                    options_df.at[instrument['bscs']['symbol'], 'StrikePrice'] = instrument['options_data']['strike_price']
                    options_df.at[instrument['bscs']['symbol'], 'Expiry'] = str(instrument['options_data']['expiration'].date())
                    options_df.at[instrument['bscs']['symbol'], 'EarningsDate'] = str(earnings_date)
                    options_df.at[instrument['bscs']['symbol'], 'Premium'] = round(instrument['options_data']['mid_pr'],2)
                    options_df.at[instrument['bscs']['symbol'], 'AllPremium'] = round(instrument['options_data']['all_pr'],2)
                    options_df.at[instrument['bscs']['symbol'], 'Bid'] = '$'+str(instrument['options_data']['bid'])
                    options_df.at[instrument['bscs']['symbol'], 'Mid'] = '$'+str(instrument['options_data']['mid'])
                    options_df.at[instrument['bscs']['symbol'], 'Ask'] = '$'+str(instrument['options_data']['ask'])
                    options_df.at[instrument['bscs']['symbol'], 'DTE'] = instrument['options_data']['dte']
                    options_df.at[instrument['bscs']['symbol'], 'DaysToEarnings'] = days_to_earnings
                    options_df.at[instrument['bscs']['symbol'], 'MCap'] = round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)

                    if grp == 'options2':
                        options_df.at[instrument['bscs']['symbol'],'total_weeks'] = instrument['price_change']['total_weeks']
                        options_df.at[instrument['bscs']['symbol'],'ten_percent_down_times'] = instrument['price_change']['ten_percent_down_times']
                        options_df.at[instrument['bscs']['symbol'],'twenty_percent_down_times'] = instrument['price_change']['twenty_percent_down_times']

                        options_df.at[instrument['bscs']['symbol'],'price_80_percent'] = instrument['options_data']['price_80_percent']
                        options_df.at[instrument['bscs']['symbol'],'noloss_point'] = instrument['options_data']['noloss_point']
                        options_df.at[instrument['bscs']['symbol'],'risk_percent'] = instrument['options_data']['risk_percent']
                        options_df.at[instrument['bscs']['symbol'],'puts_strike'] = instrument['options_data']['puts_strike']
                        options_df.at[instrument['bscs']['symbol'],'puts_premium'] = instrument['options_data']['puts_premium']
                        options_df.at[instrument['bscs']['symbol'],'twenty_percent_down'] = instrument['options_data']['twenty_percent_down']
                        options_df.at[instrument['bscs']['symbol'],'Target Price'] = instrument['AnalystRatings']['TargetPrice']
                        options_df.at[instrument['bscs']['symbol'],'WallSt Target Price'] = instrument['Highlights']['WallStreetTargetPrice']
                        options_df.at[instrument['bscs']['symbol'],'Strong Buy'] = instrument['AnalystRatings']['StrongBuy']
                        options_df.at[instrument['bscs']['symbol'],'Buy'] = instrument['AnalystRatings']['Buy']
                        options_df.at[instrument['bscs']['symbol'],'Hold'] = instrument['AnalystRatings']['Hold']
                        options_df.at[instrument['bscs']['symbol'],'Sell'] = instrument['AnalystRatings']['Sell']
                        options_df.at[instrument['bscs']['symbol'],'Strong Sell'] = instrument['AnalystRatings']['StrongSell']
                        options_df.at[instrument['bscs']['symbol'],'Earnings_Pr_Chg'] = instrument['dates']['earnings_pr_change']
                except Exception as E:
                    print("Options: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    except Exception as E:
        print("Options: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

    options_df = options_df.loc[options_df['DTE'] <= 10]
    if len(options_df) == 0:
        return
    options_df = options_df.sort_values(by=['Premium'], ascending=False)
    lcap_df = options_df.loc[options_df['MCap'] >= 50]

    #save_df_as_image(options_df, "/tmp/options_df.png")
    #save_image(options_df, "/tmp/options_df.png")

    count=6
    l = len(options_df)
    iters = math.ceil(l/count)# + 1
    #options_df = options_df.iloc[0:20]

    st = 0
    en = count
    for i in range(iters):
        message = str(i+1) +": Stocks Options:\n=====================\n"
        df = options_df.iloc[st:en]
        if len(df) == 0:
            break
        for index,d in df.iterrows():
            s = str(index) + ":" +d['Name'] +"\n" +\
                "price: $"+ str(d['Price']) + "\n" +\
                "strike_price: "+ str(d['StrikePrice']) + "\n" +\
                "expiration: "+ d['Expiry'] + "\n"
            if d['EarningsDate'] != 'nan':
                s = s + "earnings_date: "+ d['EarningsDate'] + "\n"

            if grp == 'options2':
                s = s + \
                        "10%_down_weeks: " + str(int(d['ten_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "\n" +\
                        "20%_down_weeks: " + str(int(d['twenty_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "\n" +\
                        "earnings_pr_chg: " + d['Earnings_Pr_Chg'] + "\n"
            s = s + \
                "premium: " + str(d['Premium']) + "%\n" +\
                "price+premium: " + str(d['AllPremium']) + "%\n" +\
                "bid: " + d['Bid'] + "\n" +\
                "mid: " + d['Mid'] + "\n" +\
                "ask: " + d['Ask'] + "\n" +\
                "dte: " + str(int(d['DTE'])) + " days\n"
            if not isnan(d['DaysToEarnings']):
                s = s + "days_to_earnings: " + str(int(d['DaysToEarnings'])) + "\n"

            s = s + \
                "Mcap: $" + str(d['MCap']) + "Bn\n"

            if grp == 'options2':
                s = s + \
                        "Risk Percent: " + str(d['risk_percent']) + "%\n" +\
                        "Loss_20PercentDown: " + str(d['twenty_percent_down']) + "%\n" +\
                        "Price_20PercentDown: $" + str(d['price_80_percent']) +"\n" +\
                        "NolossPoint: $" + str(d['noloss_point']) +"\n" +\
                        "PutsStrike: $" + str(d['puts_strike']) + "\n" +\
                        "PutsPremium: $" + str(d['puts_premium']) + "\n" +\
                        "Rating: " + str(d['Rating']) + "\n" +\
                        "Target Price: $" + str(d['Target Price']) + "\n" +\
                        "WallSt Target Price: $" + str(d['WallSt Target Price']) + "\n" +\
                        "Strong Buy: " + str(d['Strong Buy']) + "\n" +\
                        "Buy: " + str(d['Buy']) + "\n" +\
                        "Hold: " + str(d['Hold']) + "\n" +\
                        "Sell: " + str(d['Sell']) + "\n" +\
                        "Strong Sell: " + str(d['Strong Sell']) + "\n"

            s = s + "\n"

            message = message + s

        if grp == 'options2':
            notify_message(message, token='options2')
        else:
            notify_message(message, token='options')
        st = en
        en = en + count

    if grp == 'options2':
        count=6
        l = len(lcap_df)
        iters = math.ceil(l/count)# + 1
        #options_df = options_df.iloc[0:20]

        st = 0
        en = count
        for i in range(iters):
            message = str(i+1) +": Stocks Options:\n=====================\n"
            df = lcap_df.iloc[st:en]
            if len(df) == 0:
                break
            for index,d in df.iterrows():
                s = str(index) + ":" +d['Name'] +"\n" +\
                    "price: $"+ str(d['Price']) + "\n" +\
                    "strike_price: "+ str(d['StrikePrice']) + "\n" +\
                    "expiration: "+ d['Expiry'] + "\n"
                if d['EarningsDate'] != 'nan':
                    s = s + "earnings_date: "+ d['EarningsDate'] + "\n"

                s = s + \
                        "10%_down_weeks: " + str(int(d['ten_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "\n" +\
                        "20%_down_weeks: " + str(int(d['twenty_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "\n" +\
                        "earnings_pr_chg: " + d['Earnings_Pr_Chg'] + "\n" +\
                        "premium: " + str(d['Premium']) + "%\n" +\
                        "price+premium: " + str(d['AllPremium']) + "%\n" +\
                        "bid: " + d['Bid'] + "\n" +\
                        "mid: " + d['Mid'] + "\n" +\
                        "ask: " + d['Ask'] + "\n" +\
                        "dte: " + str(int(d['DTE'])) + " days\n"
                if not isnan(d['DaysToEarnings']):
                    s = s + "days_to_earnings: " + str(int(d['DaysToEarnings'])) + "\n"

                s = s + \
                    "Mcap: $" + str(d['MCap']) + "Bn\n" +\
                    "Risk Percent: " + str(d['risk_percent']) + "%\n" +\
                    "Loss_20PercentDown: " + str(d['twenty_percent_down']) + "%\n" +\
                    "Price_20PercentDown: $" + str(d['price_80_percent']) +"\n" +\
                    "NolossPoint: $" + str(d['noloss_point']) +"\n" +\
                    "PutsStrike: $" + str(d['puts_strike']) + "\n" +\
                    "PutsPremium: $" + str(d['puts_premium']) + "\n" +\
                    "Rating: " + str(d['Rating']) + "\n" +\
                    "Target Price: $" + str(d['Target Price']) + "\n" +\
                    "WallSt Target Price: $" + str(d['WallSt Target Price']) + "\n" +\
                    "Strong Buy: " + str(d['Strong Buy']) + "\n" +\
                    "Buy: " + str(d['Buy']) + "\n" +\
                    "Hold: " + str(d['Hold']) + "\n" +\
                    "Sell: " + str(d['Sell']) + "\n" +\
                    "Strong Sell: " + str(d['Strong Sell']) + "\n"

                s = s + "\n"

                message = message + s

            notify_message(message, token='options50')
            st = en
            en = en + count

def get_uptrend():
    fields = {
                    'Name':'',
                    'Trend':int(),
                    'Price': float(), 
                    'Day_Change': float(),
                    'Avg_Vol_X_Price_Mn': float(),
                    'Cur_Price_Max_Rsi_Change': float(),
                    'Trend_Sequence':'',
                    'Trend_Sequence_Change':'',
                    'Prev_Trend_Change':float(),
                    'MCap':float()
                }
    uptrend_df = pd.DataFrame(fields, index=[])

    c  = DB.open_db_client()
    db = c['Stocks']

    stocks = db.US_Stocks.find({"$and":[\
                                            {'General.Type':'Common Stock'},\
                                            {'General.IsDelisted': False},\
                                            {'Highlights.MarketCapitalizationMln': {"$gte":1000}},\
                                            {'technicals.sar.ta_psar_trend':{"$eq":1}},\
                                            {"$and": [ \
                                                        {'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
                                                        {'dates.mysql_price_pull_success': True},\
                                                        {'failcount.mysql_price_failcount': {'$eq': 0}},\
                                                        #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                                                    ]\
                                            }, \
                                            {"$or":[\
                                                    {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
                                                    {'price_change.date': {"$exists": False}}\
                                                    ]\
                                            },\
 
                                        ]}).batch_size(10)
    print("uptrend stocks: %d" %(stocks.count()))

    # Uptrend
    try:
        for i, instrument in enumerate(stocks):
            if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
                trend = instrument['technicals']['sar']['ta_psar_trend']
                cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
                pre_trend_pri_chg = instrument['technicals']['sar']['ta_psar_prev_trend_price_change']
                uptrend_df.loc[instrument['bscs']['symbol']] = [
                                        instrument['General']['Name'], 
                                        trend, 
                                        round(instrument['price_change']['price'],2),
                                        round(instrument['price_change']['day']*100,2),
                                        round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                                        cur_price_max_rsi_change,
                                        str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                                        str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                                        round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change'],2),
                                        round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                                        #str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
                                        ]
    except Exception as E:
        print("Uptrend: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

    if len(uptrend_df) == 0:
        return
    # Get only stocks whose previous trend has lost atleast 20%
    trend1 = uptrend_df[uptrend_df.Prev_Trend_Change< -20].sort_values(by=['Prev_Trend_Change'], ascending=True)
    trend1 = trend1[trend1.Avg_Vol_X_Price_Mn >= 60]
    trend1 = trend1.iloc[0:9]
    # Get only stocks that are atleast 5% up on today
    #trend2 = uptrend_df[uptrend_df.Day_Change >= 5].sort_values(by=['MCap'], ascending=False)
    trend2 = uptrend_df[uptrend_df.Day_Change >= 5]
    trend2 = trend2[trend2.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['Avg_Vol_X_Price_Mn'], ascending=False)
    trend2 = trend2.iloc[0:9]
    uptrend_df = pd.concat([trend1, trend2])
    uptrend_df = uptrend_df.sort_values(by=['Prev_Trend_Change'], ascending=True)
    uptrend_df.drop_duplicates(keep=False,inplace=True)
    if len(trend1) > 0:
        message = "Stocks Uptrend:\n=====================\n"
        for index,d in trend1.iterrows():
            s = str(index) + ":" +d['Name'] +"\n" +\
                    "trend: "
            if d['Trend'] > 0:
                s = s + str(d['Trend']) + "L\n"
            else:
                s = s + str(abs(d['Trend'])) + "S\n"
            s = s + "price: $"+ str(d['Price']) + "\n" +\
                "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
                "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
                "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
                "trend: " + d['Trend_Sequence'] + "\n" +\
                "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
                "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"

            message = message + s
        notify_message(message)
    if len(trend2) > 0:
        message = "Stocks Uptrend(Day Change):\n=====================\n"
        for index,d in trend2.iterrows():
            #s = str(index) + ":" +d['Name'] +"\n" +\
            #        "uptrend: "+ str(d['Trend']) + "L\n" + \
            #        "price: $"+ str(d['Price']) + "\n" +\
            #        "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
            #        "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
            #        "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
            #        "trend: " + d['Trend_Sequence'] + "\n" +\
            #        "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
            #        "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
            #        "Mcap: $" + str(d['MCap']) + "Bn\n\n"
            s = str(index) + ":" +d['Name'] +"\n" +\
                    "trend: "
            if d['Trend'] > 0:
                s = s + str(d['Trend']) + "L\n"
            else:
                s = s + str(abs(d['Trend'])) + "S\n"
            s = s + "price: $"+ str(d['Price']) + "\n" +\
                "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
                "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
                "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
                "trend: " + d['Trend_Sequence'] + "\n" +\
                "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
                "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"


            message = message + s
        notify_message(message)

def get_mstar():
    fields = {
                    'Name':'',
                    'Trend':int(),
                    'Price': float(), 
                    'Day_Change': float(),
                    'Avg_Vol_X_Price_Mn': float(),
                    'Cur_Price_Max_Rsi_Change': float(),
                    'Trend_Sequence':'',
                    'Trend_Sequence_Change':'',
                    'Prev_Trend_Change':float(),
                    'MCap':float()
                }
    mstar_df = pd.DataFrame(fields, index=[])
    c  = DB.open_db_client()
    db = c['Stocks']

    stocks = db.US_Stocks.find({"$and":[\
                                            {'General.Type':'Common Stock'},\
                                            {'General.IsDelisted': False},\
                                            {'Highlights.MarketCapitalizationMln': {"$gte":1000}},\
                                            {'technicals.candlesticks.MORNINGSTAR':{"$eq":100}},\
                                            {"$and": [ \
                                                        {'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
                                                        {'dates.mysql_price_pull_success': True},\
                                                        {'failcount.mysql_price_failcount': {'$eq': 0}},\
                                                        #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                                                    ]\
                                            }, \
                                            {"$or":[\
                                                    {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
                                                    {'price_change.date': {"$exists": False}}\
                                                    ]\
                                            },\
 
                                        ]}).batch_size(10)
    print("morning star stocks: %d" %(stocks.count()))


    # Mstar
    try:
        for i, instrument in enumerate(stocks):
            print("%d: %s: %s" %(i, instrument['bscs']['symbol'], instrument['General']['Code']))
            if 'technicals' in instrument.keys() and \
                    'sar' in instrument['technicals'].keys() and \
                    'rsi' in instrument['technicals'].keys():
                trend = instrument['technicals']['sar']['ta_psar_trend']
                cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
                mstar_df.loc[instrument['bscs']['symbol']] = [
                                        instrument['General']['Name'], 
                                        trend, 
                                        round(instrument['price_change']['price'],2),
                                        round(instrument['price_change']['day']*100,2),
                                        round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                                        cur_price_max_rsi_change,
                                        str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                                        str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                                        round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change']*100,2),
                                        round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                                        #str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
                                        ]
    except Exception as E:
        print("Mstar: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)
    if len(mstar_df) == 0:
        return

    message = "Stocks MStar:\n=====================\n"
    #mstar_df = mstar_df.sort_values(by=['MCap'], ascending=False)
    mstar_df = mstar_df[mstar_df.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['Avg_Vol_X_Price_Mn'], ascending=False)
    mstar_df = mstar_df.iloc[0:5]
    for index,d in mstar_df.iterrows():
        s = str(index) + ":" +d['Name'] +"\n" +\
                "trend: "
        if d['Trend'] > 0:
            s = s + str(d['Trend']) + "L\n"
        else:
            s = s + str(abs(d['Trend'])) + "S\n"
        s = s + "price: $"+ str(d['Price']) + "\n" +\
                "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
                "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
                "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
                "trend: " + d['Trend_Sequence'] + "\n" +\
                "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
                "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"

        message = message + s
    notify_message(message, token='mstar')

def get_indicator(indicator, conditions, fields=None):
    if fields is None:
        fields = {
                        'Name':'',
                        'Trend':int(),
                        'Price': float(), 
                        'Day_Change': float(),
                        'Avg_Vol_X_Price_Mn': float(),
                        'Cur_Price_Max_Rsi_Change': float(),
                        'Trend_Sequence':'',
                        'Trend_Sequence_Change':'',
                        'Prev_Trend_Change':float(),
                        'Days_To_Earnings':'',
                        'MCap':float()
                    }
    df = pd.DataFrame(fields, index=[])
    c  = DB.open_db_client()
    db = c['Stocks']
    collection = db.US_Stocks

    stocks = collection.find({'$and':conditions}).batch_size(10)
    #print("Indicator: %s, stocks: %d" %(indicator, stocks.count()))
    print("Indicator: %s" %(indicator))

    try:
        for i, instrument in enumerate(stocks):
            print("%d: %s: %s" %(i, instrument['bscs']['symbol'], instrument['General']['Code']))
            if 'technicals' in instrument.keys() and \
                    'sar' in instrument['technicals'].keys() and \
                    'rsi' in instrument['technicals'].keys():
                trend = instrument['technicals']['sar']['ta_psar_trend']
                cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)

                earnings_date = instrument['dates']['last_earnings_report_date'].date()
                today = dt.combine(dt.now(), dt.min.time()).date()
                days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                days = int(days)

                df.loc[instrument['bscs']['symbol']] = [
                                        instrument['General']['Name'], 
                                        trend, 
                                        round(instrument['price_change']['price'],2),
                                        round(instrument['price_change']['day']*100,2),
                                        round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                                        cur_price_max_rsi_change,
                                        str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                                        str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                                        round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change'],2),
                                        str(days), 
                                        round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                                        #str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
                                        ]
    except Exception as E:
        print("Indicator: %s: Err for sym: %s, err: %s" %(indicator, instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)
    if len(df) == 0:
        return

    message = "Stocks " + indicator + "\n=====================\n"
    #df = df.sort_values(by=['MCap'], ascending=False)
    df = df[df.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['Avg_Vol_X_Price_Mn'], ascending=False)
    df = df.iloc[0:5]
    for index,d in df.iterrows():
        s = str(index) + ":" +d['Name'] +"\n" +\
                "trend: "
        if d['Trend'] > 0:
            s = s + str(d['Trend']) + "L\n"
        else:
            s = s + str(abs(d['Trend'])) + "S\n"
        s = s + "price: $"+ str(d['Price']) + "\n" +\
                "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
                "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
                "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
                "trend: " + d['Trend_Sequence'] + "\n" +\
                "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
                "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
                "Days_To_Earnings: " + d['Days_To_Earnings'] +"\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"

        message = message + s
    notify_message(message, token=indicator)


calls = {
        ##'min_rsi': min_rsi,
        ##'max_rsi': max_rsi,
        ##'max_rsi_price': max_rsi_price,
        #'earnings_date': earnings_date,
        #'week_earnings_date':week_earnings_date,
        #'uptrend': uptrend,
        ###'downtrend': downtrend,
        #'price_change_day': price_change_day,
        #'price_change_week': price_change_week,
        }

def send_mstar_message(mstar_df):
    if len(mstar_df) == 0:
        return
    message = "Stocks MStar:\n=====================\n"
    mstar_df = mstar_df.sort_values(by=['MCap'], ascending=False)
    for index,d in mstar_df.iterrows():
        s = str(index) + ":" +d['Name'] +"\n" +\
                "trend: "+ str(d['Trend']) + "L\n" + \
                "price: $"+ str(d['Price']) + "\n" +\
                "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
                "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
                "trend: " + d['Trend_Sequence'] + "\n" +\
                "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
                "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"

        message = message + s
    notify_message(message, token='mstar')

def send_options_message(option_df):
    if len(option_df) == 0:
        return
    message = "Stocks Options:\n=====================\n"
    option_df = option_df.sort_values(by=['Premium'], ascending=False)
    for index,d in option_df.iterrows():
        s = str(index) + ":" +d['Name'] +"\n" +\
                "Price: $"+ str(d['Price']) + "\n" +\
                "StrikePrice: "+ str(d['StrikePrice']) + "\n" +\
                "Premium: "+ str(d['Premium']) +"%" + "\n" +\
                "Price+Premium: "+ str(d['AllPremium']) +"%" + "\n" +\
                "Bid: "+ str(d['Bid']) + "\n" +\
                "Mid: "+ str(d['Mid']) + "\n" +\
                "Ask: "+ str(d['Ask']) + "\n" +\
                "Dte: "+ str(d['DTE']) + "\n" +\
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"

        message = message + s
    notify_message(message, token='option')



def get_all_indicators():
    fields = {
                    'Name':'',
                    'Trend':int(),
                    'Price': float(), 
                    'Day_Change': float(),
                    'Avg_Vol_X_Price_Mn': float(),
                    'Cur_Price_Max_Rsi_Change': float(),
                    'Trend_Sequence':'',
                    'Trend_Sequence_Change':'',
                    'Prev_Trend_Change':float(),
                    'MCap':float()
                }
 
    conditions = [\
                    {'General.Type':'Common Stock'},\
                    {'General.IsDelisted': False},\
                    {'Highlights.MarketCapitalizationMln': {"$gte":1000}},\
                    {'technicals.candlesticks.MORNINGSTAR':{"$eq":100}},\
                    {"$and": [ \
                                {'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
                                {'dates.mysql_price_pull_success': True},\
                                {'failcount.mysql_price_failcount': {'$eq': 0}},\
                                #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                            ]\
                    }, \
                    {"$or":[\
                            {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
                            {'price_change.date': {"$exists": False}}\
                            ]\
                    },\
                ]

    # morning doji star
    conds = conditions + [{'technicals.candlesticks.MORNINGDOJISTAR':{"$eq":100}}]
    get_indicator('dojimstar', conds, fields)

    # morning star
    conds = conditions + [{'technicals.candlesticks.MORNINGSTAR':{"$eq":100}}]
    get_indicator('mstar', conds, fields)

    # evening doji star
    conds = conditions + [{'technicals.candlesticks.EVENINGDOJISTAR':{"$eq":100}}]
    get_indicator('dojiestar', conds, fields)

    # evening star
    conds = conditions + [{'technicals.candlesticks.EVENINGSTAR':{"$eq":100}}]
    get_indicator('estar', conds, fields)

if __name__ == "__main__":
    if len(sys.argv) == 2 and 'options' in sys.argv[1]:
        get_options(sys.argv[1])
    elif len(sys.argv) == 2 and 'ratings' in sys.argv[1]:
        get_ratings()
    elif len(sys.argv) == 2 and 'fwh' in sys.argv[1]:
        get_ratings(fwh=True)
    elif len(sys.argv) == 3 and 'ratings' in sys.argv[1] and 'pure' in sys.argv[2]:
        get_ratings(purebuy=True)
    else:
        week_earnings_date()
        #notify_radar_stocks()
        #notify_all_stocks()
        #notify_message("test")
        get_all_indicators()
        get_uptrend()
        ##get_mstar()
