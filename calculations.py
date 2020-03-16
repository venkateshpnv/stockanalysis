import conf
from conf import *
import os
import sys
import time
import math
import xlwt
from datetime import datetime

from excel import add_dcf_header, add_wb_sheet
import DB
from common import PRINT, PRINT_DBG, PRINT_ERR
from internet import get_price_growth
from excel import write_to_excel
import pprint

def calculate_PAT(stk):
    entry=[]
    try:
        for i in range(len(stk['fig']['entries'][PBT])):
            entry.append(round(stk['fig']['entries'][PBT][i] - stk['fig']['entries'][Taxes][i],2))
    except IndexError:
        return
    except TypeError:
        return
    stk['fig']['entries'].insert(PAT, entry)
    PRINT_DBG("PAT:")
    PRINT_DBG(stk['fig']['entries'][PAT])

def calculate_growth(fig, row):
    years = len(fig.entries[row])
    mid_len = math.floor(years/2)
    first = fig.entries[row][0]
    mid   = fig.entries[row][mid_len]
    last  = fig.entries[row][-1]

    PRINT_DBG("growth years: %r"%(years))
    try:
        val = int(first)
        val = int(mid)
        val = int(last)
    except:
        return 0
    # Negative growth
    if last <= 0:
        return 0
    # Ease calculation for negatives
    if first <= 0:
        first = 1
        last += abs(first)+1
    growth = round(((last/first)**(1/years)-1), 2) * years / 10
    #g2 = round(((last/mid)**(1/mid_len)-1), 2) * mid_len / 10

#   if len(fig.entries[row]) >= 5:
#       first = fig.entries[-5]
#        g5 = round(((last / first) ** (1/5) - 1), 2) * 5/10
#        ash.write()
#    if len(fig.entries[row]) >= 3:
#        first = fig.entries[-3]
#        g3 = round(((last / first) ** (1/3) - 1), 2) * 3/10

    return growth
    #return min(g1,g2)

def calc_growth(split_factor, row, years):
    if len(row) == 0:
        return 0
    if years > len(row):
        years = len(row)
    #mid_len = math.floor(years/2)
    first = row[0]
    #mid   = row[mid_len]
    last  = row[-1] * split_factor

    PRINT_DBG("growth years: %r"%(years))
    try:
        val = int(first)
        #val = int(mid)
        val = int(last)
    except:
        return 0
    # Negative growth
    if last <= 0:
        return 0
    # Ease calculation for negatives
    if first <= 0:
        first = 1
        last += abs(first)+1
    growth = round(((last/first)**(1/years)-1), 2) * years / 10
    return growth

# Calcuate numbers
def calculate_dcf(country, stk, years, data_type, criteria, beta, prices_only=False):
    if 'Years' not in stk['fig'].keys():
        PRINT_ERR("Years not found in stk[fig] for %r. Skipping...." %(stk['bscs']['symbol']))
        return False
    if len(stk['fig']['Years']) == 0:
        PRINT_ERR("No data for %s: %s, updating zero DCF Calc" %(stk['bscs']['symbol'], stk['bscs']['name']))
        return False
    if data_type != 'DB':
#       global conf.COUNT
        growth  = [0] * (GROWTH_PARAMS)
        i = 0
        startyr = stk['fig']['Years'][0]
        startyr = int(startyr.split("-")[1].lstrip().rstrip())
        PRINT(startyr)
        endyr = stk['fig']['Years'][len(stk['fig']['Years'])-2]
        endyr = int(endyr.split("-")[1].lstrip().rstrip())
        if years > len(stk['fig']['Years']):
            years = len(stk['fig']['Years'])
        #print(endyr)
        #print(stk['bscs']['split_year'])
        #print(stk['bscs']['split_factor'])
        split_factor = 1
        if stk['bscs']['split_year'] > startyr and stk['bscs']['split_year'] <= endyr:
            split_factor = stk['bscs']['split_factor']

        if prices_only is False:
            stk['fig']['price_growth']  = get_price_growth(country, stk, years, data_type)
            stk['fig']['sales_growth']  = growth[i]  = calc_growth(1, stk['fig']['Sales'], years) * len(stk['fig']['Sales']) / 10
            i+=1
            stk['fig']['profit_growth'] = growth[i]  = calc_growth(1, stk['fig']['PAT'], years) * len(stk['fig']['PAT']) / 10
            i+=1
            stk['fig']['cash_growth']   = growth[i]  = calc_growth(1, stk['fig']['CASH'], years) * len(stk['fig']['CASH']) / 10
            i+=1
            stk['fig']['book_growth']   = growth[i]  = calc_growth(split_factor, stk['fig']['BOOK'], years) * len(stk['fig']['BOOK']) / 10
            
            # Dont calculate DCF for stocks with negative growth in any factor
            if criteria == 'ONLY_POSITIVE':
                for number in growth:
                    if number <= 0:
                        print(number)
                        return False

            PRINT("Growth of entries: %r"%(growth))
            #try:
            #    stk['fig']['growth'] = min(i for i in growth if i > 0)
            #except ValueError:
            #    stk['fig']['growth'] = 0
            stk['fig']['growth'] = min(i for i in growth)

            # Calculating 20 years future earnings
            # High growth period
            stk['num']['growth_1to5'] = stk['fig']['growth']
            # Decremental growth period
            stk['num']['growth_6to8'] = round(stk['num']['growth_1to5'] * gr6to8_percent, 2)
            stk['num']['growth_9to10'] = round(stk['num']['growth_6to8'] * gr9to10_percent, 2)
            # Terminal growth
            stk['num']['growth_11to15'] = round(stk['num']['growth_9to10'] * gr11to15_percent, 2)
            stk['num']['growth_16to20'] = round(stk['num']['growth_11to15'] * gr16to20_percent, 2)
            PRINT("Growth Rates")
            PRINT("1-5 : {0:.2%}" .format(stk['num']['growth_1to5']))
            PRINT("6-8 : {0:.2%}" .format(stk['num']['growth_6to8']))
            PRINT("9-10 : {0:.2%}" .format(stk['num']['growth_9to10']))
            PRINT("11-15 : {0:.2%}" .format(stk['num']['growth_11to15']))
            PRINT("16-20 : {0:.2%}" .format(stk['num']['growth_16to20']))

            eps = stk['fig']['ttm_eps']
            growth = stk['num']['growth_1to5']
            discount = stk['num']['discount_rate']
            stk['num']['eps_20yr']=[]

            stk['num']['dcf_years'] = years
            stk['num']['fig_yr'] = int(stk['fig']['Years'][-1].split('-')[1].lstrip().rstrip())
            stk['num']['cur_yr'] = datetime.now().year
            stk['num']['term_yr'] = stk['num']['cur_yr'] + 20

            PRINT("EPS: %r"%(eps))
            PRINT("growth: %r"%(growth))
            PRINT("discount: %r"%(discount))
            for i in range(5):
                eps = eps * ((1 + growth) / (1 + discount))
                stk['num']['eps_20yr'].append(round(eps,2))
            #print(stk['num']['eps_20yr'])
            growth = stk['num']['growth_6to8']
            PRINT("growth: %r" % (growth))
            for i in range(5,8):
                eps = eps * ((1 + growth) / (1 + discount))
                stk['num']['eps_20yr'].append(round(eps,2))

            PRINT(stk['num']['eps_20yr'])
            growth = stk['num']['growth_9to10']
            PRINT("growth: %r" % (growth))
            for i in range(8,10):
                eps = eps * ((1 + growth) / (1 + discount))
                stk['num']['eps_20yr'].append(round(eps,2))
            PRINT(stk['num']['eps_20yr'])
            growth = stk['num']['growth_11to15']
            PRINT("growth: %r" % (growth))
            for i in range(10,15):
                eps = eps * ((1 + growth) / (1 + discount))
                stk['num']['eps_20yr'].append(round(eps,2))

            PRINT(stk['num']['eps_20yr'])
            growth = stk['num']['growth_16to20']
            PRINT("growth: %r" % (growth))
            for i in range(15,20):
                eps = eps * ((1 + growth) / (1 + discount))
                stk['num']['eps_20yr'].append(round(eps,2))

            PRINT("20 yrs yearly EPS: %r"%(stk['num']['eps_20yr']))
            PRINT("EPS after 5 years  : %r " % (round(stk['num']['eps_20yr'][4],2)))
            PRINT("EPS after 10 years : %r " % (round(stk['num']['eps_20yr'][9],2)))
            PRINT("EPS after 20 years : %r " % (round(stk['num']['eps_20yr'][19],2)))
            PRINT("Earnings for 5 years  : %r " % (round(sum(stk['num']['eps_20yr'][0:4]),2)))
            PRINT("Earnings for 10 years : %r " % (round(sum(stk['num']['eps_20yr'][0:9]),2)))
            PRINT("Earnings for 20 years : %r " % (round(sum(stk['num']['eps_20yr']),2)))
            #PRINT("Len : %r" %(len(stk['num'][['eps_20yr'])))

            tot_eps = sum(stk['num']['eps_20yr'])
            if tot_eps <= 0:
                tot_eps = 0
                stk['num']['inflated_eps_price'] = 0
                stk['num']['dcf_price'] = 0
                stk['num']['cp_return_rate'] = 0
                stk['num']['dcf_return_rate'] = 0
            else:
                stk['num']['inflated_eps_price'] = tot_eps * ((1 - stk['num']['inflation']) ** 20)
                stk['num']['dcf_price'] = round(stk['num']['inflated_eps_price'] * 0.5, 2)
                if beta == 'BETA':
                    if stk['bscs']['five_yr_beta'] and stk['bscs']['five_yr_beta'] >= 0:
                        stk['num']['dcf_price'] = round(stk['num']['inflated_eps_price'] * 0.5 * float(stk['bscs']['five_yr_beta']), 2)
                else:
                    stk['num']['dcf_price'] = round(stk['num']['inflated_eps_price'] * 0.5, 2)

                stk['num']['cp_return_rate'] = ((tot_eps/stk['bscs']['price']) ** (1/20)) - 1
                try:
                    stk['num']['dcf_return_rate'] = (tot_eps/stk['num']['dcf_price']) ** (1/20) - 1
                except ZeroDivisionError:
                    stk['num']['dcf_return_rate'] = 0
                #PRINT("Earnings for 20 years at %r percent inflation: %s%r" %(stk['num']['inflation']*100, RUPEE, stk['num']['inflated_eps_price']))
                #PRINT("Price at 50 percent MoS: %s%r" %(RUPEE, stk['num']['dcf_price']))
                #PRINT("Current Price: %s%r" %(RUPEE, stk['bscs']['price']))
                #PRINT("Return Rate at Current Price: {0:.2%}" .format(stk['num']['cp_return_rate']))
                #PRINT("Return Rate at MoS Price: {0:.2%}" .format(stk['num']['dcf_return_rate']))

            #if stk['bscs']['price'] <= stk['num']['dcf_price'] or stk['num']['cp_return_rate'] > 0.01:
            #if stk['bscs']['price'] <= stk['num']['dcf_price']:

    return True
    #return False

def calculate_dcf_all_stocks(country, years, data_type, criteria, beta, db_state, excel_state, prices_only=False):
    if excel_state == 'EXCEL':
        # All Stocks Excel File
        all_stk = xlwt.Workbook()
        ash = {}
        ash['Above_100bn'] = add_wb_sheet(all_stk, "Above 100 Bn")

        ash['10bn_100bn'] = add_wb_sheet(all_stk, "10Bn to 100 Bn")
        ash['5bn_10bn'] = add_wb_sheet(all_stk, "5Bn to 10 Bn")
        ash['1bn_5bn'] = add_wb_sheet(all_stk, "1Bn 5 Bn")
        ash['Below_1bn'] = add_wb_sheet(all_stk, "Below 1Bn")
        add_dcf_header(ash, years, prices_only)
    j = 0
    init_variables()

    db = DB.open_db('Stocks')
    if country == 'India':
        docs = db.Indian_Stocks.find({})
        collection = db.Indian_Stocks
        if excel_state == 'EXCEL':
            try:
                os.mkdir("./Indian_Stocks")
                os.mkdir("./Indian_Stocks/excel_files")
                os.mkdir("./Indian_Stocks/DCF_Calc")
            except FileExistsError:
                PRINT("")
        inflation = 0.08
        discount_rate = 0
        mos = 0.5
        path="./Indian_Stocks"
    elif country == 'US':
        docs = db.US_Stocks.find({})
        collection = db.US_Stocks
        if excel_state == 'EXCEL':
            try:
                os.mkdir("./US_Stocks")
                os.mkdir("./US_Stocks/excel_files")
                os.mkdir("./US_Stocks/DCF_Calc")
            except FileExistsError:
                PRINT("")
        inflation = 0
        discount_rate = 0.08
        mos = 0.5
        path="./US_Stocks"
    else:
        return

        #for doc in docs:
    no_dcf = 0
    count = 0
    for doc in collection.find({}, no_cursor_timeout=True).batch_size(10).sort([["sno",1]]):
    #for doc in collection.find({'bscs.mcap':{'$gte':10000}}, no_cursor_timeout=True).sort([["sno",1]]):
        sno = doc['sno']
        #if sno > 2913:
        if sno > 0:
            doc['id'] = doc.pop('_id')
            #doc['PAT'] = doc.pop('Profit After Taxes')
            stock = doc
            pp = pprint.PrettyPrinter(indent=4)
            #stock = DB.dbObject(**doc)
            #obj = namedtupled.map(doc)
            #obj = namedtuple("Stock", doc.keys())(*doc.values())
            #obj = json.loads(doc, object_hook=lambda d: namedtuple('Stock', d.keys())(*d.values()))
            #obj = bunchify(doc)
            
            if not stock:
                PRINT_ERR("Stock not present")
                no_dcf += 1
                continue
            if DB.ignore_stock(stock):
                no_dcf += 1
                continue
            if 'ETF' in str(stock['bscs']['name']):
                no_dcf += 1
                db.US_Stocks.update({'bscs.symbol': stock['bscs']['symbol']}, {'$set': {"ignore": "Yes"}})
                continue
            if 'Fund' in str(stock['bscs']['name']):
                no_dcf += 1
                db.US_Stocks.update({'bscs.symbol': stock['bscs']['symbol']}, {'$set': {"ignore": "Yes"}})
                continue
            if 'Trust' in str(stock['bscs']['name']):
                no_dcf += 1
                db.US_Stocks.update({'bscs.symbol': stock['bscs']['symbol']}, {'$set': {"ignore": "Yes"}})
                continue
            if 'Income Portfolio' in str(stock['bscs']['name']):
                no_dcf += 1
                db.US_Stocks.update({'bscs.symbol': stock['bscs']['symbol']}, {'$set': {"ignore": "Yes"}})
                continue
            #if stock.bscs.volume < 50000:
            #    del stock
            #    continue
            if 'price' not in stock['bscs'].keys() or stock['bscs']['price'] < 1:
                no_dcf += 1
                del stock
                continue
            # Atleast a billion
            #if stock.bscs.mcap < 1000: #millions
            # Atleast 10 billion
            #if stock.bscs.mcap < 10000: #millions
            # Between 1 billion and 10 billion
            #if stock.bscs.mcap < 1000 or stock.bscs.mcap > 10000: #millions
            #    del stock
            #    continue

            #Company Excel File
            if prices_only == False and data_type != 'NO_CALC':
                stock['num']['inflation'] = inflation
                stock['num']['discount_rate'] = discount_rate
                stock['num']['margin_of_safety'] = mos
                if calculate_dcf(country, stock, years, data_type, criteria, beta, prices_only) is False:
                    #if db_state == 'SYNC_DB':
                    if True:
                        DB.update_dummy_dcf_numbers(collection, stock)
                    del stock
                    continue
            #conf.COUNT+=1
            count+=1
            #print("count: %r, symb: %r" %(count, stock['bscs']['symbol']))
            print("%d: %s: %s"%(sno, stock['bscs']['symbol'], stock['bscs']['name']))
            if excel_state == 'EXCEL':
                com = xlwt.Workbook()
                write_to_excel(country, com, ash, stock, years, prices_only)
                excel = "%s/excel_files/%s.xls" % (path, stock['bscs']['name'])
                PRINT("Writing to %s" % (excel))
                com.save(excel)
                del com
            if db_state == 'SYNC_DB':
                DB.update_dcf_numbers(collection, stock)
            j+=1

            del stock
            stock=None
            com=None

    print("Stocks Calculated: %r" %(j))
    print("No DCF: %r" %(no_dcf))
    now = datetime.now().date()
    if prices_only:
        excel = "%s/DCF_Calc/All_Stocks_Prices_%s.xls" % (path, str(now))
    else:
        excel = "%s/DCF_Calc/All_Stocks_DCF_%s.xls" % (path, str(now))
    if excel_state == 'EXCEL':
        if len(sys.argv) == 2:
            excel = "%s/DCF_Calc/%s.xls" %(path, sys.argv[1])
        print("Saving DCF stocks to %s"%(excel))
        all_stk.save(excel)


