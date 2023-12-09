import json
import xlrd
import xlwt
import urllib, requests
from xlwt import Workbook, Formula
from datetime import timedelta

from datastructures import *
from common import *
import DB

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

def notify_message(message):
    if message is None or message == "":
        return

    chat_id = get_telegram_chat_id()
    token = get_telegram_token_id()
    url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
        token, chat_id, urllib.parse.quote_plus(message))
    resp = requests.get(url, timeout=10)
    #print(resp)

def get_instrument(sym, db_client):
    if sym is None or sym == "":
        print("Error: Symbol is empty, pass one")
        return None

    if db_client is None:
        print("Error: db_client is empty, pass one")
        return None

    db = db_client['Stocks']
    stocks = db.US_Stocks
    db = db_client['Cryptos']
    cryptos = db.Cryptos
    #db = db_client['ETFs']
    #etfs = db.ETFs

    stks = stocks.find({'bscs.symbol':sym})
    cryptos = cryptos.find({'bscs.symbol':sym})
    #etfs = etfs.find({'bscs.symbol':sym})
    if stks.count() != 0:
        instrument = stks[0]
    elif cryptos.count() != 0:
        instrument = cryptos[0]
    #elif etfs.count() != 0:
    #    instrument = etfs[0]
    else:
        print("Instrument: %s doesn't exist" %(sym))
        return None
    
    str = 'Symbol: '+ instrument['bscs']['symbol']
    if 'General' in instrument.keys():
        if 'Code' in instrument['General'].keys():
            str = str + ' Name: ' + instrument['General']['Code']
        elif 'Name' in instrument['General'].keys():
            str = str + ' Name: ' + instrument['General']['Name'] +' '
        if 'Type' in instrument['General'].keys():
            str = str + instrument['General']['Type']
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
        if trend > 0 and trend <= 3:
            message = sym + " : uptrend: "+ str(trend) + "L\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def downtrend(instrument):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']
    if 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        trend = instrument['technicals']['sar']['ta_psar_trend']
        if trend < 0 and trend >= -3:
            message = sym + " : downtrend: "+ str(trend) + "S\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def price_change_day(instrument):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']
    if 'price_change' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        change = instrument['price_change']['day'] * 100
        if change <= -5 or change >= 4.5:
            message = sym + " : price_change_day: "+ str(change) + "%\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def price_change_week(instrument):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']
    if 'price_change' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        change = instrument['price_change']['week'] * 100
        if change <= -10 or change >= 10:
            message = sym + " : price_change_week: "+ str(change) + "%\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def earnings_date(instrument):
    if instrument is None:
        return

    sym = instrument['bscs']['symbol']
    if 'dates' in instrument.keys() and 'last_earnings_report_date' in instrument['dates'].keys() and 'technicals' in instrument.keys() and 'sar' in instrument['technicals'].keys():
        dt = instrument['dates']['last_earnings_report_date']
        # If earnings is tomorrow, send a notification
        if dt+timedelta(1) == dt.now().date():
            message = sym + " : earnings_date: "+ str(dt) + "\n trend: " + instrument['technicals']['sar']['ta_psar_trend_sequence']
            notify_message(message)

def notify_radar_stocks(country='US'):
    if country != 'US':
        return

    wb = xlrd.open_workbook(radar_stocks_file)
    if wb.nsheets < 1:
        print("No sheets found")
        return

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
                for call in calls.values():
                    call(instrument)

    finally:
        DB.close_db_client(db_client)


calls = {
        'min_rsi': min_rsi,
        #'max_rsi': max_rsi,
        'max_rsi_price': max_rsi_price,
        'uptrend': uptrend,
        #'downtrend': downtrend,
        'price_change_day': price_change_day,
        'price_change_week': price_change_week,
        'earnings_date': earnings_date,
        }


notify_radar_stocks()
