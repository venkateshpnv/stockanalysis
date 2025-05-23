import json
import xlrd
import xlwt
import urllib, requests
from xlwt import Workbook, Formula
from datetime import timedelta
from datetime import datetime as dt
import time
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import gridspec
import copy
import math
from math import nan, isnan
import os

from bokeh.io import export_png, export_svgs
from bokeh.models import ColumnDataSource, DataTable, TableColumn

#import matplotlib.pyplot as plt
#import pandas as pd
#from pandas.table.plotting import table

from datastructures import *
import DB
from common import *
import hdf5

def save_df_as_image(df, path="df_image.png"):
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
    return path

# Function to wrap text for better readability
def wrap_text(text, width=15):
    if isinstance(text, str):
        return "\n".join(textwrap.wrap(text, width))
    return text  # Return numbers as is

# Function to convert DataFrame to high-resolution image
def dataframe_to_image(df, image_path="df_image.png", wrap_text=True,banner=None):
    #if wrap_text:
    #    df = df.applymap(lambda x: wrap_text(str(x)))

    fig, ax = plt.subplots(figsize=(6, 2), dpi=600)  # Increase figure size & DPI
    ax.axis("tight")
    ax.axis("off")

    if banner:
        ax.set_title('banner', fontsize=16, fontweight='bold')
        plt.text(0.5, 0.9, banner, fontsize=10, fontweight="bold", ha="center",
                bbox=dict(facecolor="lightblue", edgecolor="black", boxstyle="round,pad=0.1"), color="white",
                transform=ax.transAxes)  # Blue background, white text

    table = ax.table(
        cellText=df.values, 
        colLabels=df.columns, 
        cellLoc="center", 
        loc="center",
        colColours=["#f2b134"] * df.shape[1]  # Header color
    )

    table.auto_set_font_size(False)
    #table.set_fontsize(12)  # Increase font size
    #table.scale(2, 2)  # Scale table for better clarity

    for i, key in enumerate(df.columns):
        table.auto_set_column_width([i])

    plt.savefig(image_path, bbox_inches="tight", dpi=600)  # High DPI
    plt.close()

    return image_path


# Function to convert DataFrame to high-resolution image
def dataframe_to_image2(df, image_path="df_image.png", banner=None):
    max_height = 1200
    fixed_width = 800
    dpi = 100

    # Calculate dynamic height based on rows but cap it
    row_height_px = 40
    calculated_height = int(0.15 * fixed_width + len(df) * row_height_px)
    final_height = min(calculated_height, max_height)

    fig_width_in = fixed_width / dpi
    fig_height_in = final_height / dpi

    fig = plt.figure(figsize=(fig_width_in, fig_height_in), dpi=dpi)
    gs = gridspec.GridSpec(2, 1, height_ratios=[0.15, 0.85], figure=fig)

    # Banner section
    if banner:
        ax_banner = fig.add_subplot(gs[0])
        ax_banner.axis("off")
        ax_banner.text(0.5, 0.5, banner, fontsize=12, fontweight="bold", ha="center", va="center",
                       bbox=dict(facecolor="lightblue", edgecolor="black", boxstyle="round,pad=0.3"), color="white")

    # Table section
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis("off")

    table = ax_table.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="center",
        loc="center",
        colColours=["#f2b134"] * df.shape[1]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.0, 1.2)

    for i in range(len(df.columns)):
        table.auto_set_column_width([i])

    plt.tight_layout(pad=0.5)
    plt.savefig(image_path, bbox_inches="tight", dpi=dpi, format="png")
    plt.close()
    return image_path

# Function to send image to Telegram group
def send_telegram_photo(image_path, token='stock_notify'):
    time.sleep(1)
    chat_id = get_telegram_chat_id(token=token)
    token = get_telegram_token_id(token=token)

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    with open(image_path, "rb") as photo:
        response = requests.post(url, data={"chat_id": chat_id}, files={"photo": photo})
    return response.json()

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
def earnings_week(earnings_dates=True, earnings_results=True):
    week_df = pd.DataFrame(columns=['Date', 'Sym', 'Name', 'MCap', 'Price', 'Tr_Seq', 'Time', 'Week Change'])
    three_week_df = pd.DataFrame(columns=['Date', 'Sym', 'Name', 'MCap', 'Price', 'Tr_Seq', 'Time', 'Week Change'])
    today_df = pd.DataFrame(columns=['Date', 'Sym', 'Name', 'MCap', 'Price', 'Tr_Seq', 'Time', 'Week Change'])
    earnings_df = pd.DataFrame(columns=['Date', 'Sym', 'Name', 'Price_Change', 'MCap', 'Price', 'Time'])

    #fields = {
    #                'Name':'',
    #                'Trend':int(),
    #                'Price': float(), 
    #                'Day_Change': float(),
    #                'Avg_Vol_X_Price_Mn': float(),
    #                'Cur_Price_Max_Rsi_Change': float(),
    #                'Trend_Sequence':'',
    #                'Trend_Sequence_Change':'',
    #                'Prev_Trend_Change':float(),
    #                'Days_To_Earnings':'',
    #                'MCap':float()
    #            }
    c  = DB.open_db_client()
    db = c['Stocks']
    Mn = 1000000
    Bn = 1000*Mn
    Bn = 1000000000
    today = DB.trading_day(dt.combine(dt.now().date(), dt.min.time()))
    #today = DB.trading_day(dt.combine(dt.strptime("2024-07-23", "%Y-%m-%d").date(), dt.min.time()))
    yesterday = DB.get_previous_trading_day(today)
    week = DB.trading_day(today + timedelta(6))
    three_weeks = DB.trading_day(today + timedelta(6+7+7+7)) # make it four weeks

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
                    {"$or":[\
                                {'General.Sector': {"$in": ['Technology', 'Communication Services', ]}},\
                                {"$and": [ \
                                            {'General.Sector': {"$nin": ['Technology', 'Communication Services', ]}},\
                                            {'General.Code' : {"$in": non_tech_stocks}},\
                                        ]\
                                },\
                                {"$and": [ \
                                            {'General.Code' : {"$in": selected_stocks}},\
                                        ]\
                                },\
                            ]\
                    },\
                    {'Highlights.MarketCapitalization': {'$gte': 5 * Bn}},\
                ]
    week_conditions = conditions + \
                                    [
                                        {"$and": [\
                                                    {'dates.ndaq_last_earnings_date' :{"$gt":today}},\
                                                    {'dates.ndaq_last_earnings_date' :{"$lte":week}},\
                                            ]\
                                        },\
                                    ]
    three_week_conditions = conditions + \
                                    [
                                        {"$and": [\
                                                    {'dates.ndaq_last_earnings_date' :{"$gt":week}},\
                                                    {'dates.ndaq_last_earnings_date' :{"$lte":three_weeks}},\
                                            ]\
                                        },\
                                    ]

    conditions2 = [ \
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
                    {"$or":[\
                                {'General.Sector': {"$in": ['Technology', 'Communication Services', ]}},\
                                {"$and": [ \
                                            {'General.Sector': {"$nin": ['Technology', 'Communication Services', ]}},\
                                            {'General.Code' : {"$in": non_tech_stocks}},\
                                        ]\
                                },\
                            ]\
                    },\
                    {'Highlights.MarketCapitalization': {'$gte': 5 * Bn}},\
                    {"$or": [\
                                {"$and": [\
                                            {'dates.ndaq_last_earnings_date' :{"$eq":today}},\
                                            {'dates.ndaq_earnings_calc_date' :{"$eq":today}},\
                                            {'dates.ndaq_last_earnings_time' :{"$in":["BeforeMarket", np.nan]}},\
                                    ]\
                                },\
                                {"$and": [\
                                            {'dates.ndaq_last_earnings_date' :{"$eq":yesterday}},\
                                            {'dates.ndaq_last_earnings_time' :{"$in":["AfterMarket", None]}},\
                                    ]\
                                },\
                            ]\
                    },\
                    {"$or": [\
                                {'price_change.ndaq_earnings_change' : {"$lte": -0.05}},\
                                {'price_change.ndaq_earnings_change' : {"$gte": 0.05}},\
                            ]\
                    },\
                ]

    week_earnings_stks = {}
    tomorrow_earnings_stks = {}
    three_week_earnings_stks = []

    try:
        if earnings_dates:
            stocks = db.US_Stocks.find({'$and':week_conditions}).sort([["dates.ndaq_last_earnings_date",1]]).allow_disk_use(True)
            print("Week earnings stocks: ", stocks.count())
            for i, instrument in enumerate(stocks):
                print("%s: %s" %(instrument['bscs']['symbol'], instrument['General']['Name']))
                # Earnings dates
                if 'dates' in instrument.keys() and 'ndaq_last_earnings_date' in instrument['dates'].keys():
                    if 'ndaq_last_earnings_time' not in instrument['dates'].keys():
                        instrument['dates']['ndaq_last_earnings_time']=''
                    edate = instrument['dates']['ndaq_last_earnings_date'].date()
                    sym = instrument['bscs']['symbol']
                    if edate >= dt.now().date() and edate <= dt.now().date() + timedelta(6):
                        if sym not in week_earnings_stks.keys():
                            week_earnings_stks[sym] = instrument['bscs']['symbol']
                            week_df.loc[i] = [str(edate), sym, instrument['General']['Name'], round(instrument['Highlights']['MarketCapitalizationMln']/1000,2), instrument['price_change']['price'], str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']), instrument['dates']['ndaq_last_earnings_time'], instrument['price_change']['week']] 
                    # If earnings is tomorrow, send a notification
                    if edate == dt.now().date() + timedelta(1) or edate == DB.get_next_trading_day():
                        if sym not in tomorrow_earnings_stks.keys():
                            today_df.loc[i] = [str(edate), sym, instrument['General']['Name'], round(instrument['Highlights']['MarketCapitalizationMln']/1000,2), instrument['price_change']['price'], str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']), instrument['dates']['ndaq_last_earnings_time'], instrument['price_change']['week']]
                            #tomorrow_earnings_stks[sym] = {'Name': instrument['General']['Name'], 'Time': instrument['dates']['ndaq_last_earnings_time'], 'MCap': round(instrument['Highlights']['MarketCapitalizationMln']/1000,2)}

            stocks = db.US_Stocks.find({'$and':three_week_conditions}).sort([["dates.ndaq_last_earnings_date",1]]).allow_disk_use(True)
            print("stocks with earnings from next week to next three weeks: ", stocks.count())
            for i, instrument in enumerate(stocks):
                print("%s: %s" %(instrument['bscs']['symbol'], instrument['General']['Name']))
                # Earnings dates
                if 'dates' in instrument.keys() and 'ndaq_last_earnings_date' in instrument['dates'].keys():
                    if 'ndaq_last_earnings_time' not in instrument['dates'].keys():
                        instrument['dates']['ndaq_last_earnings_time'] = ''
                    edate = instrument['dates']['ndaq_last_earnings_date'].date()
                    sym = instrument['bscs']['symbol']
                    if sym not in three_week_earnings_stks:
                        three_week_earnings_stks.append(instrument['bscs']['symbol'])
                        three_week_df.loc[i] = [str(edate), sym, instrument['General']['Name'], round(instrument['Highlights']['MarketCapitalizationMln']/1000,2), instrument['price_change']['price'], str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']), instrument['dates']['ndaq_last_earnings_time'], instrument['price_change']['week']]
            def get_last_three_trends(trend_string):
                """Extracts the last three trend values from the string."""
                trends = trend_string.split('-')
                return '-'.join(trends[-3:])

            def get_last_three_values(s):
                try:
                    values = s.split(',')
                    if len(values) > 1:
                        return ','.join(values[-3:])
                    else:
                        return ""
                except AttributeError:
                    return ""
            week_df['Tr_Seq'] = week_df['Tr_Seq'].apply(get_last_three_values)
            today_df['Tr_Seq'] = today_df['Tr_Seq'].apply(get_last_three_values)
            three_week_df['Tr_Seq'] = three_week_df['Tr_Seq'].apply(get_last_three_values)

            week_df = week_df.sort_values(by=['Date', 'MCap'], ascending=[True, False])
            today_df = today_df.sort_values(by=['Date', 'MCap'], ascending=[True, False])

            three_week_df = three_week_df.loc[three_week_df["Week Change"] <= -0.05]
            three_week_df = three_week_df.sort_values(by=['Week Change'], ascending=[True])

            week_df["Week Change"] = week_df["Week Change"].apply(lambda x: f"{x * 100:.2f}%")
            today_df["Week Change"] = today_df["Week Change"].apply(lambda x: f"{x * 100:.2f}%")
            three_week_df["Week Change"] = three_week_df["Week Change"].apply(lambda x: f"{x * 100:.2f}%")

            # strip the company name from second space to avoid long names
            week_df['Name'] = week_df['Name'].str.split(' ').str[:2].str.join(' ')
            today_df['Name'] = today_df['Name'].str.split(' ').str[:2].str.join(' ')
            three_week_df['Name'] = three_week_df['Name'].str.split(' ').str[:2].str.join(' ')

            week_df['Price'] = '$' + week_df['Price'].astype(str)
            today_df['Price'] = '$' + today_df['Price'].astype(str)
            three_week_df['Price'] = '$' + three_week_df['Price'].astype(str)

            count=40
            if len(three_week_df) > 0:
                st=0
                en=count
                l = len(three_week_df)
                iters = math.ceil(l/count)
                for i in range(iters):
                    df = three_week_df[st:en]
                    if len(df) == 0:
                        break
                    #message = "Earnings in Four Weeks\n"
                    #notify_message(message, token='earnings_dates')
                    image_path = dataframe_to_image2(df, banner="Earnings in Four Weeks")
                    send_telegram_photo(image_path, token='earnings_dates')
                    st = en
                    en = en + count

            if len(week_df) > 0:
                st=0
                en=count
                l = len(week_df)
                iters = math.ceil(l/count)
                for i in range(iters):
                    df = week_df[st:en]
                    if len(df) == 0:
                        break
                    #message = "Earnings in 7 days\n"
                    #notify_message(message, token='earnings_dates')
                    image_path = dataframe_to_image2(df, banner="Earnings in 7 days")
                    send_telegram_photo(image_path, token='earnings_dates')
                    #image_path = save_df_as_image(week_df)
                    #send_telegram_photo(image_path, token='earnings_dates')

                #for index, d in week_df.iterrows():
                #    s = d['Sym'] + ":" + d['Name'] + "\n" +\
                #            "MCap: " + str(d['MCap']) + "Bn\n" +\
                #            "Time : " + str(d['Time']) + "\n" +\
                #            "earnings_date: "+ str(d['Date']) +"\n\n"
                #    message = message + s
                #notify_message(message, token='earnings_dates')

            if len(today_df) > 0:
                st=0
                en=count
                l = len(today_df)
                iters = math.ceil(l/count)
                for i in range(iters):
                    df = today_df[st:en]
                    if len(df) == 0:
                        break
 
                    #message = "Earnings Tomorrow\n"
                    #notify_message(message, token='earnings_dates')
                    image_path = dataframe_to_image2(today_df, banner="Earnings Tomorrow")
                    send_telegram_photo(image_path, token='earnings_dates')

                #for index, d in today_df.iterrows():
                #    s = d['Sym'] + ":" + d['Name'] + "\n" +\
                #            "MCap: " + str(d['MCap']) + "Bn\n" +\
                #            "Time : " + str(d['Time']) + "\n" +\
                #            "earnings_date: "+ str(d['Date']) +"\n\n"
                #    message = message + s
                #notify_message(message, token='earnings_dates')

        if earnings_results:
            stocks = db.US_Stocks.find({'$and':conditions2}).sort([["dates.ndaq_last_earnings_date",1]]).allow_disk_use(True)
            print("Stocks with earnings today: ", stocks.count())
            #earnings_df = pd.DataFrame(columns=['Date', 'Sym', 'Name', 'Price_Change', 'MCap', 'Time'])
            stks = []
            for i, instrument in enumerate(stocks):
                sym = instrument['bscs']['symbol']
                if sym not in stks:
                    stks.append(sym)
                    if 'dates' in instrument.keys() and 'ndaq_last_earnings_date' in instrument['dates'].keys():
                        edate = instrument['dates']['ndaq_last_earnings_date'].date()
                    else:
                        edate = ""
                    earnings_df.loc[i] = [str(edate), sym, instrument['General']['Name'], round(instrument['price_change']['ndaq_earnings_change']*100, 2), round(instrument['Highlights']['MarketCapitalizationMln']/1000,2), instrument['price_change']['price'], instrument['dates']['ndaq_last_earnings_time']]

            if len(earnings_df) > 0:
                up_df = earnings_df[earnings_df['Price_Change'] >= 0]
                up_df = up_df.sort_values(by=['Price_Change'], ascending=[False])
                down_df = earnings_df[earnings_df['Price_Change'] < 0]
                down_df = down_df.sort_values(by=['Price_Change'], ascending=[True])

                if len(down_df) > 0:
                    #message = "Earnings Down :\n=====================\n"
                    #for index, d in down_df.iterrows():
                    #    s = d['Sym'] + ":" + d['Name'] + "\n" +\
                    #            "MCap: " + str(d['MCap']) + "Bn\n" +\
                    #            "Time : " + str(d['Time']) + "\n" +\
                    #            "earnings_date: "+ str(d['Date']) + "\n" +\
                    #            "price_change: "+ str(d['Price_Change']) + "%\n\n"
                    #    message = message + s
                    #notify_message(message, token='earnings_dates')

                    down_df['Price_Change'] = down_df['Price_Change'].astype(str) + '%'
                    image_path = dataframe_to_image2(down_df, banner="Earnings Price Down")
                    send_telegram_photo(image_path, token='earnings_dates')
                if len(up_df) > 0:
                    #message = "Earnings Up:\n=====================\n"
                    #for index, d in up_df.iterrows():
                    #    s = d['Sym'] + ":" + d['Name'] + "\n" +\
                    #            "MCap: " + str(d['MCap']) + "Bn\n" +\
                    #            "Time : " + str(d['Time']) + "\n" +\
                    #            "earnings_date: "+ str(d['Date']) + "\n" +\
                    #            "price_change: "+ str(d['Price_Change']) + "%\n\n"
                    #    message = message + s
                    #notify_message(message, token='earnings_dates')
                    up_df['Price_Change'] = up_df['Price_Change'].astype(str) + '%'
                    image_path = dataframe_to_image2(up_df, banner="Earnings Price Up")
                    send_telegram_photo(image_path, token='earnings_dates')

    finally:
        DB.close_db_client(c)

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

def get_ratings(fwh=False, purebuy=False, tech=True):
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
                    'MCap':float(),
                    'Avg_Vol_X_Price_Mn': float(),
                    'with_52week_high': float()
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
        conditions.append({'price_change.price_times_avg_vol_in_mn':{'$gte':60}})
    if tech is True:
        conditions.append({"$or":[\
                                    {'General.Sector': 'Technology'},\
                                    {"$and": [ \
                                                {'General.Sector': {"$nin": ['Technology']}},\
                                                {'General.Code' : {"$in": non_tech_stocks}},\
                                            ]\
                                    },\
                                ]\
                            })
 
    else:
        conditions.append({'Highlights.MarketCapitalization':{'$gte':5 * Bn}})
 
    # Get top 10 stocks with StrongBuy rating
    if fwh is True:
        stocks = db.US_Stocks.find({'$and':conditions}).sort([["price_change.with_52week_high", 1]]).allow_disk_use(True).sort([["price_change.year", -1]]).allow_disk_use(True)#.limit(100)
    else:
        #stocks = db.US_Stocks.find({'$and':conditions}).sort([["AnalystRatings.Rating", -1]]).allow_disk_use(True).limit(100)
        stocks = db.US_Stocks.find({'$and':conditions}).sort([["AnalystRatings.StrongBuy", -1]]).allow_disk_use(True).limit(100)

    print("Fifty Two Week High stocks: %d" %(stocks.count()))

    td = dt.now()
    try:
        for i, instrument in enumerate(stocks):
            #if i > 100:
            #    break
            try:
                earnings_date = instrument['dates']['last_earnings_report_date'].date()
                today = dt.combine(dt.now(), dt.min.time()).date()
                days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                days_to_earnings = int(days)

                df.at[instrument['bscs']['symbol'], 'Name'] = instrument['General']['Name']

                df.at[instrument['bscs']['symbol'],'total_weeks'] = instrument['price_change']['total_weeks']
                df.at[instrument['bscs']['symbol'],'ten_percent_down_times'] = instrument['price_change']['ten_percent_down_times']
                df.at[instrument['bscs']['symbol'],'twenty_percent_down_times'] = instrument['price_change']['twenty_percent_down_times']
                if 'AnalystRatings' in instrument.keys():
                    df.at[instrument['bscs']['symbol'],'Rating'] = instrument['AnalystRatings']['Rating']
                    df.at[instrument['bscs']['symbol'],'Target Price'] = instrument['AnalystRatings']['TargetPrice']
                    df.at[instrument['bscs']['symbol'],'WallSt Target Price'] = instrument['Highlights']['WallStreetTargetPrice']
                    df.at[instrument['bscs']['symbol'],'Strong Buy'] = instrument['AnalystRatings']['StrongBuy']
                    df.at[instrument['bscs']['symbol'],'Buy'] = instrument['AnalystRatings']['Buy']
                    df.at[instrument['bscs']['symbol'],'Hold'] = instrument['AnalystRatings']['Hold']
                    df.at[instrument['bscs']['symbol'],'Sell'] = instrument['AnalystRatings']['Sell']
                    df.at[instrument['bscs']['symbol'],'Strong Sell'] = instrument['AnalystRatings']['StrongSell']
                df.at[instrument['bscs']['symbol'], 'Price'] = instrument['price_change']['price']
                #df.at[instrument['bscs']['symbol'], 'Price'] = instrument['options_data']['price']
                df.at[instrument['bscs']['symbol'], 'StrikePrice'] = instrument['options_data']['strike_price']
                if isinstance(instrument['options_data']['expiration'], td.__class__):
                    df.at[instrument['bscs']['symbol'], 'Expiry'] = str(instrument['options_data']['expiration'].date())
                df.at[instrument['bscs']['symbol'], 'EarningsDate'] = str(earnings_date)
                df.at[instrument['bscs']['symbol'], 'Premium'] = round(instrument['options_data']['mid_pr'],2)
                df.at[instrument['bscs']['symbol'], 'AllPremium'] = round(instrument['options_data']['all_pr'],2)
                df.at[instrument['bscs']['symbol'], 'Bid'] = '$'+str(instrument['options_data']['bid'])
                df.at[instrument['bscs']['symbol'], 'Mid'] = '$'+str(instrument['options_data']['mid'])
                df.at[instrument['bscs']['symbol'], 'Ask'] = '$'+str(instrument['options_data']['ask'])
                if 'dte' in instrument['options_data'].keys():
                    df.at[instrument['bscs']['symbol'], 'DTE'] = instrument['options_data']['dte']
                df.at[instrument['bscs']['symbol'], 'DaysToEarnings'] = days_to_earnings
                df.at[instrument['bscs']['symbol'], 'MCap'] = round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                if fwh:
                    df.at[instrument['bscs']['symbol'], 'YearChange'] = instrument['price_change']["year"]
                df.at[instrument['bscs']['symbol'], 'Avg_Vol_X_Price_Mn'] = round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2)
                df.at[instrument['bscs']['symbol'],'with_52week_high'] = instrument['price_change']['with_52week_high']

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

    df = df[df.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['with_52week_high'], ascending=False)
    df = df[df['with_52week_high'] >= -0.02]
    df = df.sort_values(by=['ten_percent_down_times'], ascending=False)

    #df = df.loc[df['DTE'] < 10]

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
        message = str(i+1) +": 52 Week High Stocks:\n=====================\n"
        sdf = df.iloc[st:en]
        if len(sdf) == 0:
            break
 
        for index,d in sdf.iterrows():
            s = str(index) + ":" +d['Name'] +"\n" +\
                    "Rating: " + str(d['Rating']) + "\n" +\
                    "Target Price: $" + str(d['Target Price']) + "\n" +\
                    "WallSt Target Price: $" + str(d['WallSt Target Price']) + "\n" +\
                    "price: $"+ str(d['Price']) + "\n" +\
                    "with_52week_high: " + str(round(d['with_52week_high']*100,2)) + "%\n" +\
                    "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
                    "earnings_date: "+ d['EarningsDate'] + "\n" +\
                    "10%_down_weeks: " + str(int(d['ten_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "\n" +\
                    "20%_down_weeks: " + str(int(d['twenty_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "\n" +\
                    "days_to_earnings: " + str(d['DaysToEarnings']) + " days\n" +\
                    "Mcap: $" + str(d['MCap']) + "Bn\n"
                    #"strike_price: "+ str(d['StrikePrice']) + "\n" +\
                    #"expiration: "+ d['Expiry'] + "\n" +\
                    #"Strong Buy: " + str(d['Strong Buy']) + "\n" +\
                    #"Buy: " + str(d['Buy']) + "\n" +\
                    #"Hold: " + str(d['Hold']) + "\n" +\
                    #"Sell: " + str(d['Sell']) + "\n" +\
                    #"Strong Sell: " + str(d['Strong Sell']) + "\n" +\
                    #"premium: " + str(d['Premium']) + "%\n" +\
                    #"price+premium: " + str(d['AllPremium']) + "%\n" +\
                    #"bid: " + d['Bid'] + "\n" +\
                    #"mid: " + d['Mid'] + "\n" +\
                    #"ask: " + d['Ask'] + "\n" +\
                    #"dte: " + str(d['DTE']) + " days\n" +\
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
    if fwh:
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
        conditions.append({'Highlights.MarketCapitalization':{'$gte':1 * Bn}})
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
                        
                #if 'earnings_pull_date' not in instrument['options_data'].keys() or \
                #    instrument['options_data']['earnings_pull_date'] < DB.get_latest_trading_day():

                #    url='https://api.marketdata.app/v1/stocks/earnings/'+instrument['bscs']['symbol']+'/'
                #    today = dt.now().date()
                #    frm = str(today - timedelta(today.weekday()))
                #    #to = str(today + timedelta(4 - today.weekday()))

                #    if today.weekday() >= 4:
                #        #to = (7 - (today.weekday() + 1)) + 5
                #        to = str(today + timedelta((7 - (today.weekday() + 1)) + 5))
                #    else:
                #        # 0-Mon,1-Tue,2-Wed,3-Thu,4-Fri,5-Sat,6-Sun
                #        #to = 4 - today.weekday()
                #        to = str(today + timedelta(4 - today.weekday()))
 
                #    url = url + '?from=' + frm + '&to=' + to 
                #    ret = requests.get(url, headers=headers)
                #    if ret.status_code > 203:
                #        print("Failed to get earnings data for %r, error code: %r, error: %r" %(instrument['bscs']['symbol'], ret.status_code, ret.text))
                #    else:
                #        edf=pd.DataFrame(ret.json())
                #        if len(edf) > 0 and edf.iloc[0]['reportDate'] != None:
                #            try:
                #                earnings_date = pd.to_datetime(edf.iloc[0]['reportDate'],unit='s')
                #                earnings_date = dt.combine(earnings_date.to_pydatetime(), dt.min.time())
                #            except:
                #                pass
                #        instrument['options_data']['earnings_report_date'] = earnings_date
                #        DB.update_field(db.US_Stocks, instrument['bscs']['symbol'], 'options_data.earnings_report_date', earnings_date)

                #    instrument['options_data']['earnings_pull_date'] = dt.combine(dt.now(), dt.min.time())
                #    DB.update_field(db.US_Stocks, instrument['bscs']['symbol'], 'options_data.earnings_pull_date', instrument['options_data']['earnings_pull_date'])


                bid = instrument['options_data']['bid']
                ask = instrument['options_data']['ask']
                percent_diff = ((ask-bid)/bid) * 100
                if percent_diff > 200:
                    continue

                td = dt.now()
                days_to_earnings = nan
                earnings_date = nan
                #if 'earnings_report_date' in instrument['options_data'].keys() and isinstance(instrument['options_data']['earnings_report_date'], td.__class__):
                if 'dates' in instrument.keys() and 'ndaq_last_earnings_date' in instrument['dates'].keys():
                    earnings_date = instrument['dates']['ndaq_last_earnings_date'].date()
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
                        options_df.at[instrument['bscs']['symbol'],'max_loss_percent'] = instrument['options_data']['max_loss_percent']
                        options_df.at[instrument['bscs']['symbol'],'max_loss_price_down'] = instrument['options_data']['max_loss_price_down']
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

    options_df = options_df.loc[options_df['DTE'] <= 9]
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
                        "10%down_weeks: " + str(int(d['ten_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "(" +\
                            str(round((int(d['ten_percent_down_times'])/int(d['total_weeks']))*100,2)) +"%)\n" +\
                        "20%down_weeks: " + str(int(d['twenty_percent_down_times'])) + "/" + str(int(d['total_weeks'])) +"(" +\
                            str(round((int(d['twenty_percent_down_times'])/int(d['total_weeks']))*100,2)) +"%)\n" +\
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
                        #"Risk Percent: " + str(d['risk_percent']) + "%\n" +\
                        #"Loss_20PercentDown: " + str(d['twenty_percent_down']) + "%\n" +\
                        #"Price_20PercentDown: $" + str(d['price_80_percent']) +"\n" +\
                s = s + \
                        "NoLossPoint: $" + str(d['noloss_point']) +"\n" +\
                        "MaxLoss%: " + str(d['max_loss_percent']) +"%\n" +\
                        "MaxLossPriceDown: " + str(d['max_loss_price_down']) +"%\n" +\
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
                        "10%down_weeks: " + str(int(d['ten_percent_down_times'])) + "/" + str(int(d['total_weeks'])) + "(" +\
                            str(round((int(d['ten_percent_down_times'])/int(d['total_weeks']))*100,2)) +"%)\n" +\
                        "20%down_weeks: " + str(int(d['twenty_percent_down_times'])) + "/" + str(int(d['total_weeks'])) +"(" +\
                            str(round((int(d['twenty_percent_down_times'])/int(d['total_weeks']))*100,2)) +"%)\n" +\
                        "earnings_pr_chg: " + d['Earnings_Pr_Chg'] + "\n" +\
                        "premium: " + str(d['Premium']) + "%\n" +\
                        "price+premium: " + str(d['AllPremium']) + "%\n" +\
                        "bid: " + d['Bid'] + "\n" +\
                        "mid: " + d['Mid'] + "\n" +\
                        "ask: " + d['Ask'] + "\n" +\
                        "dte: " + str(int(d['DTE'])) + " days\n"
                if not isnan(d['DaysToEarnings']):
                    s = s + "days_to_earnings: " + str(int(d['DaysToEarnings'])) + "\n"

                    #"Risk Percent: " + str(d['risk_percent']) + "%\n" +\
                    #"Loss_20PercentDown: " + str(d['twenty_percent_down']) + "%\n" +\
                    #"Price_20PercentDown: $" + str(d['price_80_percent']) +"\n" +\
                s = s + \
                    "Mcap: $" + str(d['MCap']) + "Bn\n" +\
                    "NolossPoint: $" + str(d['noloss_point']) +"\n" +\
                    "MaxLoss%: " + str(d['max_loss_percent']) +"%\n" +\
                    "MaxLossPriceDown: " + str(d['max_loss_price_down']) +"%\n" +\
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

def get_uptrend(selected=False):
    fields = {
                    'Name':'',
                    'Trend':int(),
                    'Price': float(), 
                    'Day_Change': float(),
                    'Year_Change': float(),
                    'Avg_Vol_X_Price_Mn': float(),
                    'Cur_Price_Max_Rsi_Change': float(),
                    'Trend_Sequence':'',
                    'Trend_Sequence_Change':'',
                    'Prev_Trend_Change':float(),
                    'Cur_Trend_Change':float(),
                    'MCap':float()
                }
    uptrend_df = pd.DataFrame(fields, index=[])

    c  = DB.open_db_client()
    db = c['Stocks']

    conditions = [\
                     #{"$and": [ \
                     #            {'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
                     #            {'dates.mysql_price_pull_success': True},\
                     #            {'failcount.mysql_price_failcount': {'$eq': 0}},\
                     #            #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
                     #        ]\
                     #}, \
                     #{"$or":[\
                     #        {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
                     #        {'price_change.date': {"$exists": False}}\
                     #        ]\
                     #},\
 
                 ]
    if selected:
        conditions.append(
                            {"$and":[\
                                        {'General.Code' : {"$in": selected_stocks}},\
                                        {'technicals.sar.date':{'$gte': DB.get_latest_trading_day()}},\
                                    ]\
                            }
                        )
    else:
        conditions.append({'General.Type':'Common Stock'})
        conditions.append({'General.IsDelisted': False})
        conditions.append({"$or":[\
                                        {'General.Sector': 'Technology'},\
                                        {"$and": [ \
                                                    {'General.Sector': {"$nin": ['Technology']}},\
                                                    {'General.Code' : {"$in": non_tech_stocks}},\
                                                ]\
                                        },\
                                    ]\
                            })
        conditions.append({'Highlights.MarketCapitalizationMln': {"$gte":5000}})
        conditions.append(
                            {"$and":[\
                                    {"$or":[\
                                                {"$and": [ \
                                                            {'technicals.sar.ta_psar_trend':{"$eq":1}},\
                                                            {'technicals.sar.ta_psar_prev_trend':{"$lte":-10}},\
                                                        ]\
                                                },\
                                                {'technicals.sar.ta_psar_trend':{"$lte":-15}},\
                                                {'technicals.sar.ta_psar_cur_trend_price_change':{"$lte":-0.15}},\
                                            ]\
                                    },\
                                    {'technicals.sar.date':{'$gte': DB.get_latest_trading_day()}},\
                                ]\
                            }
                        )

    stocks = db.US_Stocks.find({"$and": conditions}).batch_size(10)
    #stocks = list(db.US_Stocks.find({"$and": conditions}))
    #res2 = list(db.US_Stocks.find({"$and":[\
    #                                        {'General.Type':'Common Stock'},\
    #                                        {'General.IsDelisted': False},\
    #                                        {'Highlights.MarketCapitalizationMln': {"$gte":50000}},\
    #                                        {'General.Code' : {"$in": non_tech_stocks}},\
    #                                        {"$or":[\
    #                                                    {"$and": [ \
    #                                                                {'technicals.sar.ta_psar_trend':{"$eq":1}},\
    #                                                                {'technicals.sar.ta_psar_prev_trend':{"$lte":-10}},\
    #                                                            ]\
    #                                                    },\
    #                                                    {'technicals.sar.ta_psar_trend':{"$lte":-15}},\
    #                                                ]\
    #                                        },\
    #                                        #{"$and": [ \
    #                                        #            {'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
    #                                        #            {'dates.mysql_price_pull_success': True},\
    #                                        #            {'failcount.mysql_price_failcount': {'$eq': 0}},\
    #                                        #            #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
    #                                        #        ]\
    #                                        #}, \
    #                                        #{"$or":[\
    #                                        #        {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
    #                                        #        {'price_change.date': {"$exists": False}}\
    #                                        #        ]\
    #                                        #},\
 
    #                                    ]}))
    #combined_results = res1 + res2
    #stocks = {doc['_id']: doc for doc in combined_results}.values()

    #stocks = db.US_Stocks.find({"$and":[\
    #                                        {'General.Type':'Common Stock'},\
    #                                        {'General.IsDelisted': False},\
    #                                        {'General.Sector': 'Technology'},\
    #                                        {'Highlights.MarketCapitalizationMln': {"$gte":50000}},\
    #                                        {"$or":[\
    #                                                    {"$and": [ \
    #                                                                {'technicals.sar.ta_psar_trend':{"$eq":1}},\
    #                                                                {'technicals.sar.ta_psar_prev_trend':{"$lte":-10}},\
    #                                                            ]\
    #                                                    },\
    #                                                    {'technicals.sar.ta_psar_trend':{"$lte":-15}},\
    #                                                ]\
    #                                        },\
    #                                        {"$and": [ \
    #                                                    {'dates.mysql_price_date': {"$gte": DB.get_latest_trading_day()}},\
    #                                                    {'dates.mysql_price_pull_success': True},\
    #                                                    {'failcount.mysql_price_failcount': {'$eq': 0}},\
    #                                                    #{'failcount.mysql_price_failcount': {'$lt': MAX_FAIL_COUNT}},\
    #                                                ]\
    #                                        }, \
    #                                        {"$or":[\
    #                                                {'price_change.date': {"$gte":DB.get_latest_trading_day()}},\
    #                                                {'price_change.date': {"$exists": False}}\
    #                                                ]\
    #                                        },\
 
    #                                    ]}).batch_size(10)

    #print("uptrend stocks: %d" %(len(stocks)))
    print("uptrend stocks: %d" %(stocks.count()))

    results_list = list(stocks)
    if selected:
        sorted_results = sorted(results_list, key=lambda doc: selected_stocks.index(doc['General']['Code']))
    else:
        sorted_results = results_list

    # Uptrend
    try:
        for i, instrument in enumerate(sorted_results):
        #for i, instrument in enumerate(stocks):
            print(instrument['General']['Code'])
            if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
                trend = instrument['technicals']['sar']['ta_psar_trend']
                cur_price_max_rsi_change = round(instrument['technicals']['rsi']['cur_price_max_rsi_change']*100, 2)
                pre_trend_pri_chg = instrument['technicals']['sar']['ta_psar_prev_trend_price_change']
                if instrument['bscs']['symbol'] in US_indices:
                    uptrend_df.loc[instrument['bscs']['symbol']] = [
                                            instrument['General']['Name'], 
                                            trend, 
                                            round(instrument['price_change']['price'],2),
                                            round(instrument['price_change']['day']*100,2),
                                            round(instrument['price_change']['year']*100,2),
                                            round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                                            cur_price_max_rsi_change,
                                            str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                                            str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                                            round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change']*100,2),
                                            round(instrument['technicals']['sar']['ta_psar_cur_trend_price_change']*100,2),
                                            0
                                            #str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
                                            ]
                else:
                    uptrend_df.loc[instrument['bscs']['symbol']] = [
                                            instrument['General']['Name'], 
                                            trend, 
                                            round(instrument['price_change']['price'],2),
                                            round(instrument['price_change']['day']*100,2),
                                            round(instrument['price_change']['year']*100,2),
                                            round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                                            cur_price_max_rsi_change,
                                            str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                                            str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                                            round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change']*100,2),
                                            round(instrument['technicals']['sar']['ta_psar_cur_trend_price_change']*100,2),
                                            round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2),
                                            ]
    except Exception as E:
        print("Uptrend: Err for sym: %s, err: %s" %(instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

    if len(uptrend_df) == 0:
        return

    if not selected:
        ## Get only stocks whose previous trend has lost atleast 10%
        #trend1 = uptrend_df[uptrend_df.Prev_Trend_Change< -10].sort_values(by=['Prev_Trend_Change'], ascending=True)
        trend1 = uptrend_df[(uptrend_df['Trend'] == 1) & (uptrend_df['Prev_Trend_Change'] < -10)]
        trend1 = trend1[trend1.Avg_Vol_X_Price_Mn >= 60]
        trend1 = trend1.sort_values(by='Prev_Trend_Change', ascending=True)
        trend1 = trend1.iloc[0:9]
        ## Get only stocks that are atleast 5% up on today
        ##trend2 = uptrend_df[uptrend_df.Day_Change >= 5].sort_values(by=['MCap'], ascending=False)
        #trend2 = uptrend_df[uptrend_df.Day_Change >= 5]
        #trend2 = trend2[trend2.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['Avg_Vol_X_Price_Mn'], ascending=False)
        #trend2 = trend2.iloc[0:9]
        # Get stocks where current trend is down by atleast 10%
        trend3 = uptrend_df[uptrend_df.Cur_Trend_Change <= -10]
        trend3 = trend3[trend3.Avg_Vol_X_Price_Mn >= 60]
        #trend3 = trend3[trend3.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['Avg_Vol_X_Price_Mn'], ascending=False)
        #trend3 = trend3.iloc[0:9]
        trend3 = trend3.sort_values(by=['Cur_Trend_Change'], ascending=True)
        uptrend_df = pd.concat([trend1, trend3])
        #uptrend_df = uptrend_df.sort_values(by=['Prev_Trend_Change'], ascending=True)

        #df1 = uptrend_df[uptrend_df.Trend == 1]
        #df2 = uptrend_df[uptrend_df.Trend < 1]
        #df1 = df1.sort_values(by=['Trend', 'Prev_Trend_Change'],ascending=[False, True])
        #df2 = df2.sort_values(by=['Cur_Trend_Change'],ascending=[True])
        #uptrend_df = df1.append(df2)

        uptrend_df.drop_duplicates(keep=False,inplace=True)

    if len(uptrend_df) == 0:
        return
    def get_last_three_trends(trend_string):
        """Extracts the last three trend values from the string."""
        trends = trend_string.split('-')
        return '-'.join(trends[-3:])

    def get_last_three_values(s):
        try:
            values = s.split(',')
            if len(values) > 1:
                return ','.join(values[-3:])
            else:
                return ""
        except AttributeError:
            return ""

    uptrend_df['Trend_Sequence_Change'] = uptrend_df['Trend_Sequence_Change'].apply(get_last_three_values)
    uptrend_df.rename(columns={'Trend': 'Tr', 'Prev_Trend_Change': 'PTChg', 'Cur_Trend_Change':'CTChg', 'Trend_Sequence_Change':'Tr_Seq'}, inplace=True)
    uptrend_df['Name'] = uptrend_df['Name'].str.split(' ').str[:2].str.join(' ')
    uptrend_df['Sym'] = uptrend_df.index
    uptrend_df['PTChg'] = uptrend_df['PTChg'].astype(str)  + '%'
    uptrend_df['CTChg'] = uptrend_df['CTChg'].astype(str) + '%'
    uptrend_df['MCap'] = uptrend_df['MCap'].astype(str) + 'Bn'
    image_path = dataframe_to_image2(uptrend_df[['Sym', 'Name', 'Price', 'Tr', 'Tr_Seq', 'PTChg', 'CTChg', 'MCap']])
    if selected:
        send_telegram_photo(image_path, token='selected_stocks')
    else:
        send_telegram_photo(image_path, token='stock_notify')
    return

    #if not selected:
    #    count = 6
    #else:
    #    count = 10
    #st = 0
    #en = count
    #l = len(uptrend_df)
    #iters = math.ceil(l/count)# + 1
    #if len(uptrend_df) > 0:
    #    for i in range(iters):
    #        if not selected:
    #            message = str(i+1) +": Stocks Uptrend/long downtrend:\n=====================\n"
    #        else:
    #            message = str(i+1) +": Selected Stocks:\n======================\n"

    #        df = uptrend_df.iloc[st:en]
    #        if len(df) == 0:
    #            break
    #        for index,d in df.iterrows():
    #            s = str(index) + ":" +d['Name'] +"\n"
    #            if not selected:
    #                s = s + "trend: "
    #                if d['Trend'] > 0:
    #                    s = s + str(d['Trend']) + "L\n"
    #                else:
    #                    s = s + str(abs(d['Trend'])) + "S\n"

    #            s = s + "price: $"+ str(d['Price']) + "\n" +\
    #                "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
    #                "year change: "+ str(d['Year_Change']) +"%" + "\n" +\
    #                "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n"

    #            if not selected:
    #                s = s + "trend: " + d['Trend_Sequence'] + "\n"

    #            s = s + "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
    #                "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n"

    #            if not selected:
    #                s = s + "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
    #                        "Mcap: $" + str(d['MCap']) + "Bn\n"
    #            s = s + "\n"
    #            message = message + s
    #        if selected:
    #            notify_message(message, token='selected_stocks')
    #        else:
    #            notify_message(message)
    #        st = en
    #        en = en + count
    #if not selected and len(trend2) > 0:
    #    message = "Stocks Uptrend(Day Change):\n=====================\n"
    #    for index,d in trend2.iterrows():
    #        #s = str(index) + ":" +d['Name'] +"\n" +\
    #        #        "uptrend: "+ str(d['Trend']) + "L\n" + \
    #        #        "price: $"+ str(d['Price']) + "\n" +\
    #        #        "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
    #        #        "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
    #        #        "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
    #        #        "trend: " + d['Trend_Sequence'] + "\n" +\
    #        #        "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
    #        #        "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
    #        #        "Mcap: $" + str(d['MCap']) + "Bn\n\n"
    #        s = str(index) + ":" +d['Name'] +"\n" +\
    #                "trend: "
    #        if d['Trend'] > 0:
    #            s = s + str(d['Trend']) + "L\n"
    #        else:
    #            s = s + str(abs(d['Trend'])) + "S\n"
    #        s = s + "price: $"+ str(d['Price']) + "\n" +\
    #            "day change: "+ str(d['Day_Change']) +"%" + "\n" +\
    #            "year change: "+ str(d['Year_Change']) +"%" + "\n" +\
    #            "cur_price_max_rsi_change: "+ str(d['Cur_Price_Max_Rsi_Change']) + "%\n" +\
    #            "Avg_Vol_X_Price: " + str(d['Avg_Vol_X_Price_Mn']) + " Mn\n" + \
    #            "trend: " + d['Trend_Sequence'] + "\n" +\
    #            "trend_change: " + d['Trend_Sequence_Change'] + "\n" +\
    #            "prev_trend_change: " + str(d['Prev_Trend_Change']) +"%" +"\n" +\
    #            "Mcap: $" + str(d['MCap']) + "Bn\n\n"


    #        message = message + s
    #    notify_message(message)

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

                #earnings_date = instrument['dates']['last_earnings_report_date'].date()
                #today = dt.combine(dt.now(), dt.min.time()).date()
                #days = date_difference(today, earnings_date, holidays=get_holiday_list(earnings_date, today))
                #days = int(days)

                #df.loc[instrument['bscs']['symbol']] = [
                #                        instrument['General']['Name'], 
                #                        trend, 
                #                        round(instrument['price_change']['price'],2),
                #                        round(instrument['price_change']['day']*100,2),
                #                        round((instrument['price_change']['price']*instrument['price_change']['avg_volume'])/1000000,2),
                #                        cur_price_max_rsi_change,
                #                        str(instrument['technicals']['sar']['ta_psar_trend_sequence']),
                #                        str(instrument['technicals']['sar']['ta_psar_trend_pcnt_change']),
                #                        round(instrument['technicals']['sar']['ta_psar_prev_trend_price_change'],2),
                #                        str(days), 
                #                        round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)
                #                        #str(round(instrument['Highlights']["MarketCapitalizationMln"]/1000,2)) + "Bn"
                #                        ]
                df.loc[instrument['bscs']['symbol']] = [
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
        print("Indicator: %s: Err for sym: %s, err: %s" %(indicator, instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

    message = "Stocks " + indicator + "\n=====================\n"
    #df = df.sort_values(by=['MCap'], ascending=False)
    df = df[df.Avg_Vol_X_Price_Mn >= 60].sort_values(by=['Avg_Vol_X_Price_Mn'], ascending=False)
    if len(df) == 0:
        return
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
                "Mcap: $" + str(d['MCap']) + "Bn\n\n"
                #"Days_To_Earnings: " + d['Days_To_Earnings'] +"\n" +\

        message = message + s
    notify_message(message, token=indicator)

def get_rsi_min(indicator, conditions, fields=None):
    df = pd.DataFrame(columns=['Sym', 'Name', 'MCap', 'RSI', 'Price',])

    c  = DB.open_db_client()
    db = c['Stocks']
    collection = db.US_Stocks

    stocks = collection.find({'$and':conditions}).batch_size(10)
    #print("Indicator: %s, stocks: %d" %(indicator, stocks.count()))
    print("Indicator: %s" %(indicator))

    try:
        for i, instrument in enumerate(stocks):
            print("%d: %s: %s" %(i, instrument['bscs']['symbol'], instrument['General']['Name']))
            if 'technicals' in instrument.keys() and \
                    'rsi' in instrument['technicals'].keys():
                df.loc[i] = [instrument['General']['Code'], instrument['General']['Name'], round(instrument['Highlights']['MarketCapitalizationMln']/1000,2), round(instrument['technicals']['rsi']['latest'],2), instrument['price_change']['price']]

        df['Name'] = df['Name'].str.split(' ').str[:2].str.join(' ')
        df['Price'] = '$' + df['Price'].astype(str)
        df = df.sort_values(by=['MCap'], ascending=[False])
        df = df.iloc[0:10]
        if len(df) > 0:
            image_path = dataframe_to_image(df)
            send_telegram_photo(image_path, token='rsi_min')

    except Exception as E:
        print("Indicator: %s: Err for sym: %s, err: %s" %(indicator, instrument['bscs']['symbol'], str(E)))
    finally:
        DB.close_db_client(c)

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
                    #{"$or":[\
                    #            {'General.Sector': 'Technology'},\
                    #            {"$and": [ \
                    #                        {'General.Sector': {"$nin": ['Technology']}},\
                    #                        {'General.Code' : {"$in": non_tech_stocks}},\
                    #                    ]\
                    #            },\
                    #        ]\
                    #},\
                    {'Highlights.MarketCapitalizationMln': {"$gte":1000}},\
                    #{'technicals.candlesticks.MORNINGSTAR':{"$eq":100}},\
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
    try:
        conds = conditions + [{'technicals.candlesticks.MORNINGDOJISTAR':{"$eq":100}}]
        get_indicator('dojimstar', conds, fields)
    except:
        pass

    # Min rsi
    try:
        conds = conditions + [{'technicals.rsi.with_60day_min':{"$eq":0}}]
        conds = conds + [\
                    {"$or":[\
                                {'General.Sector': 'Technology'},\
                                {"$and": [ \
                                            {'General.Sector': {"$nin": ['Technology']}},\
                                            {'General.Code' : {"$in": non_tech_stocks}},\
                                        ]\
                                },\
                            ]\
                    },\
                    ]
 
        get_rsi_min('rsi_min', conds)
    except exception as E:
        print("mstar error: %r" %(str(E)))
        pass

    # morning star
    try:
        conds = conditions + [{'technicals.candlesticks.MORNINGSTAR':{"$eq":100}}]
        get_indicator('mstar', conds, fields)
    except exception as E:
        print("mstar error: %r" %(str(E)))
        pass

    # evening doji star
    try:
        conds = conditions + [{'technicals.candlesticks.EVENINGDOJISTAR':{"$eq":100}}]
        get_indicator('dojiestar', conds, fields)
    except:
        pass

    # evening star
    try:
        conds = conditions + [{'technicals.candlesticks.EVENINGSTAR':{"$eq":100}}]
        get_indicator('estar', conds, fields)
    except:
        pass

if __name__ == "__main__":
    if is_holiday():
        sys.exit(0)
    if len(sys.argv) == 2 and 'options' in sys.argv[1]:
        get_options(sys.argv[1])
    elif len(sys.argv) == 2 and 'ratings' in sys.argv[1]:
        get_ratings()
    elif len(sys.argv) == 2 and 'fwh' in sys.argv[1]:
        get_ratings(fwh=True)
    elif len(sys.argv) == 2 and 'earnings_dates' in sys.argv[1]:
        earnings_week(earnings_dates=True, earnings_results=False)
    elif len(sys.argv) == 2 and 'earnings_results' in sys.argv[1]:
        earnings_week(earnings_dates=False, earnings_results=True)
    elif len(sys.argv) == 3 and 'ratings' in sys.argv[1] and 'pure' in sys.argv[2]:
        get_ratings(purebuy=True)
    else:
        ##week_earnings_date()
        earnings_week(earnings_dates=False, earnings_results=True)
        ##notify_radar_stocks()
        ##notify_all_stocks()
        ##notify_message("test")
        get_all_indicators()
        get_uptrend()
        get_uptrend(selected=True)
        #get_ratings(fwh=True)
        #get_mstar()
