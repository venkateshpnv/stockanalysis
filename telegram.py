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

from datastructures import *
import DB
from common import *
import hdf5

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
    #for i, stk in enumerate(stocks):
    #        price_change_week(stk)

    #send_uptrend_message(uptrend_df)
    send_mstar_message(mstar_df)

    DB.close_db_client(c)

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

week_earnings_date()
#notify_radar_stocks()
#notify_all_stocks()
#notify_message("test")
get_all_indicators()
get_uptrend()
##get_mstar()
