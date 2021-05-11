import sys
# Excel operations
import xlrd
import xlwt
from xlwt import Workbook, Formula

from pprint import pprint

# Date
import datetime
from datetime import datetime as dt, timedelta
#from datetime import date
import arrow
import markdown

import conf
import DB
import conf
import internet
import parse_html
from common import *
import  hdf5
from datastructures import *

pattern = xlwt.Pattern()
pattern.pattern = xlwt.Pattern.SOLID_PATTERN
pattern.pattern_fore_colour = xlwt.Style.colour_map['yellow']

style_bold = xlwt.Style.easyxf("font: bold 1;")
#style2 = xlwt.Style.easyxf("font: bold 1, fore_colour green;")
#style2 = xlwt.Style.easyxf('pattern: pattern solid, fore_colour green;')
#style3 = xlwt.Style.easyxf("""
#    font: name Arial;
#    borders: left thin, top thin, bottom thick;
#    pattern: pattern solid, fore_colour light_green;
#    """, num_format_str='YYYY-MM-DD')

style_percent = xlwt.Style.easyxf(num_format_str="0.00%")
style_decimal = xlwt.Style.easyxf(num_format_str="0.00")
#TODO bold decimal style
style_wrap = xlwt.XFStyle()
style_wrap.alignment.wrap = 1
style_wrap.alignment.horz = xlwt.Alignment.HORZ_RIGHT
style_wrap.font.bold = 1
style_wrap.font.height = 10 * 20 #(10 pt)

style_text = xlwt.XFStyle()
style_text.alignment.wrap = 1
style_text.alignment.horz = xlwt.Alignment.HORZ_RIGHT
#style_text.font.bold = 0
style_text.font.height = 10 * 20 #(10 pt)

style_num = xlwt.XFStyle()
style_num.alignment.wrap = 1
style_num.alignment.horz = xlwt.Alignment.HORZ_RIGHT
#style_text.font.bold = 0
style_num.font.height = 10 * 20 #(10 pt)

style_highlight = xlwt.XFStyle()
style_highlight.pattern = pattern

def sh_write(exl_sht, row, column, data, style=None, all_sht=None):
    try:
        if style:
            exl_sht.write(row, column, data, style)
        else:
            exl_sht.write(row, column, data)
        if all_sht:
            if style:
                all_sht.write(row, column, data, style)
            else:
                all_sht.write(row, column, data)
 
    except:
        pass

def add_wb_sheet(workbook, sheet_name, horz_pos=1, vert_pos=16):
    sheet = workbook.add_sheet(sheet_name)
    sheet.set_panes_frozen(True) 
    sheet.set_horz_split_pos(horz_pos) 
    sheet.set_vert_split_pos(vert_pos) 
    return sheet

def get_usd_to_inr():
    page = internet.get_webpage("http://www.dollar2rupee.net")
    soup = parse_html.get_soup(page)
    conversion_rate = soup.find("tr").find_next("tr").find_next("tr").find_all("td")[5].get_text()
    entry = []
    entry.append("USD to INR")
    entry.append(conversion_rate)
    return entry

def get_symbol_prices(sym, name, country, index, shortlist_price):
    entry = []
    sql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
    if not index:
        entry.append(sym)
    entry.append(name)
    price = DB.mysql_get_latest_price(sql_engine, country, sym)
    if not index:
        stk =  DB.get_stock_from_db(country, sym)
        if stk['fig']['betas']['six_months']:
            entry.append(str(round(stk['fig']['betas']['six_months']['beta'], 2)))
        else:
            entry.append("-")
        del stk
    entry.append(str(round(price,2)))

    if not index:
        entry.append(str(shortlist_price))
        if type(shortlist_price) is not str:
            since_shortlist = price / shortlist_price - 1  
            entry.append(str(round(since_shortlist*100, 2))+'%')
        else:
            entry.append(' ')

    try:
        query = 'select * from {} order by Date desc limit 2'.format(DB.get_symbol_table_name(sym))
        df = DB.read_from_sql(query, sql_engine)
        if not df.empty:
            if index:
                entry.append(str(round((df['Adj Close'][0] - df['Adj Close'][1]),2)))
            df = df.iloc[0]
            entry.append(str(round(df['Day Change']*100, 2))+'%')
            entry.append(str(round(df['Week Change']*100, 2))+'%')
            entry.append(str(round(df['Month Change']*100, 2))+'%')
            entry.append(str(round(df['Quarter Change']*100, 2))+'%')
            entry.append(str(round(df['Half Year Change']*100, 2))+'%')
            entry.append(str(round(df['Year Change']*100, 2))+'%')
            if index:
                entry.append(str(round(df['Five Year Change']*100, 2))+'%')
                entry.append(str(round(df['Ten Year Change']*100, 2))+'%')
    except Exception as e:
        print("excel.py: get_symbol_prices(): %r" %(str(e)))
        sys.exit()

    DB.close_sql_connection(sql_engine)
    #print(entry)
    return entry
 
def get_radar_stocks(country):
    if country != 'US':
        return

    wb = xlrd.open_workbook(radar_stocks_file)
    if wb.nsheets < 1:
        print("No sheets found")
        return

    entries = []
    s = parse_html.html_head()
    
    # USD to INR
    print("USD to INR")
    entries.append(get_usd_to_inr())
    entries.append([""])
    s = parse_html.html_set_line(s)
    s = parse_html.html_text(s, entries)
    s = parse_html.html_set_line(s)
    
    ##Indices
    entries = []
    head = [ "Index", "Price", "Points", "Day Change", "Week Change", "Month Change", "Quarter Change", "Half Year", "Year Change", "5 Year Change", "10 Year Change"]
    #print(head)
    entries.append(head)
    entry = []
    print("Indices")
    #entries.append(get_symbol_prices("BSE", "BSE", 'India', 1, 0))
    #entries.append(get_symbol_prices("NSE", "NSE", 'India', 1, 0))
    entries.append(get_symbol_prices("SP500", "S&P 500", 'US', 1, 0))
    entries.append(get_symbol_prices("DowJones", "Dow Jones", 'US', 1, 0))
    entries.append(get_symbol_prices("Nasdaq", "Nasdaq", 'US', 1, 0))
    entries.append(get_symbol_prices("Russel2000", "Russel 2000", 'US', 1, 0))
    entries.append([""])
    #entries.append([""])
    s = parse_html.html_text(s, entries)
    s = parse_html.html_set_line(s)

    f=open("/tmp/radar.html","w")
    f.write(s)
    f.close()
    for j in range(1,wb.nsheets):
        entries = []
        sheet = wb.sheet_by_index(j)
        s = parse_html.html_text(s, [wb.sheet_names()[j]])
        s = parse_html.html_set_line(s)
        #Stocks
        head=["Symbol", "Name", "6MBeta", "Price", "Shlist Price", "Since Shlist", "Day Change", "Week Change", "Month Change", "Quarter Change", "Half Year", "Year Change"]
        entries.append(head)
        #for i in range(1,3):
        for i in range(1,sheet.nrows):
            entry = []
            sym  = str(sheet.cell_value(i, 0))
            if sym == '':
                continue
            name = str(sheet.cell_value(i, 1))
            print("Symbol: %r, Name: %r" %(sym, name))
            #print("\"%s\"" %(sheet.cell_value(i,4)))
            s_price = sheet.cell_value(i,3)
            if type(s_price) is str and len(s_price) == 0:
                shortlist_price = ' '
            else:
                shortlist_price = float(sheet.cell_value(i, 3))


            entries.append(get_symbol_prices(sym, name, 'US', None, shortlist_price))
            ##print(entries)
        s = parse_html.html_text(s, entries)
        s = parse_html.html_set_line(s)
        #s = markdown.markdown(entries)
        #print(s)
    subject = 'Radar Stocks :' + str(dt.now().date())
    print(subject)
    f=open("stocks.html","w")
    f.write(s)
    f.close()
    internet.send_email2('petlafin@gmail.com', 'Tasche3#Gm', 'petlafin@gmail.com', subject, s)
    #internet.send_email(s)

def get_India_stock_split_info(stk):
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
def get_India_symbol_and_sector(stk):
    wb = xlrd.open_workbook(conf.bse_stocks)
    sheet = wb.sheet_by_index(0)
    #sheet.cell_value(0,0)

    for i in range(1,sheet.nrows):
        if str(int(sheet.cell_value(i, 0))) == stk['bscs']['bse_symbol']:
            stk['bscs']['symbol'] = sheet.cell_value(i,1)
            stk['bscs']['sector'] = sheet.cell_value(i,7)
            return
    PRINT_ERR("Cant find symbol name for %s" %(stk['bscs']['bse_symbol']))


def add_basic_header(sheet, i):
    sheet.row(0).height_mismatch = True
    sheet.row(0).height = 3*367
    #Company
    sheet.col(i).width = 13*367
    sheet.write(0, i, "Company", style_wrap)
    conf.COMP=i

    i+=1
    #Symbol
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Symbol", style_wrap)
    conf.SYM=i

    i+=1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Sector", style_wrap)
    conf.SEC=i

    i+=1
    sheet.col(i).width =10*367
    sheet.write(0, i, "Industry", style_wrap)
    conf.IND=i

    i+=1
    #Since
    sheet.col(i).width = 3*367
    sheet.write(0, i, "IPODate", style_wrap)
    conf.SINCE=i

    i+=1
    #Current Price Date
    sheet.col(i).width = 3*367
    sheet.write(0, i, "Current Price Date", style_wrap)
    conf.CUR_PR_DT=i

    i+=1
    #Current Price
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Current Price", style_wrap)
    conf.CUR_PR=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "50 MA", style_wrap)
    conf.FIFTY_DAY_MA=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "200 MA", style_wrap)
    conf.TWO_HUNDRED_DAY_MA=i

    i+=1
    #52 Week High
    sheet.col(i).width = 5*367
    sheet.write(0, i, "52Wk Hgh", style_wrap)
    conf.F2WK_HG=i

    i+=1
    #52 Week Low
    sheet.col(i).width = 5*367
    sheet.write(0, i, "52Wk Lw", style_wrap)
    conf.F2WK_LW=i

    i+=1
    #52 Week Low
    sheet.col(i).width = 6*367
    sheet.write(0, i, "With 52Wk Lw", style_wrap)
    conf.W_F2WK_LW=i

    i+=1
    #52 Week Low
    sheet.col(i).width = 6*367
    sheet.write(0, i, "With 52Wk Hgh", style_wrap)
    conf.W_F2WK_HG=i

    i+=1
    #Volume
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Volume", style_wrap)
    conf.VOL=i

    i+=1
    #Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "1M Beta", style_wrap)
    conf.ONE_BETA=i

    i+=1
    #Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "3M Beta", style_wrap)
    conf.THREE_BETA=i

    i+=1
    #Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "6M Beta", style_wrap)
    conf.SIX_BETA=i

    i+=1
    #Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "1Yr Beta", style_wrap)
    conf.YEAR_BETA=i

    i+=1
    #Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "5Yr Beta", style_wrap)
    conf.FIVE_BETA=i


    i+=1
    #Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Whole Beta", style_wrap)
    conf.W_BETA=i


    #i+=1
    ## Face Value
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Face Value", style_wrap)
    #conf.FV=i

    i+=1
    # Market Cap in Cr
    sheet.col(i).width = 8*367
    sheet.write(0, i, "MCap Millions", style_wrap)
    conf.MCAP=i

    #i+=1
    ## Market Cap in Cr
    #sheet.col(i).width = 8*367
    #sheet.write(0, i, "Revenue Millions", style_wrap)
    #conf.REVENUE=i


    ##i+=1
    ### conf.FII
    ##sheet.col(i).width = 5*367
    ##sheet.write(0, i, "FII", style_wrap)
    ##conf.FII=i

    #i+=1
    ## conf.DII
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "DII", style_wrap)
    #conf.DII=i

    #i+=1
    ## Promoter Stake
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Prom Stake", style_wrap)
    #conf.PRM_S=i

    i+=1
    # RSI
    sheet.col(i).width = 5*367
    st = "RSI"
    sheet.write(0, i, st, style_wrap)
    conf.RSI=i

    i+=1
    # difference between 60 day min RSI and latest RSI
    sheet.col(i).width = 5*367
    st = "RSI Min Diff"
    sheet.write(0, i, st, style_wrap)
    conf.RSI_MIN_DIFF=i

    i+=1
    # difference between 60 day min RSI and latest RSI
    sheet.col(i).width = 5*367
    st = "RSI Max Diff"
    sheet.write(0, i, st, style_wrap)
    conf.RSI_MAX_DIFF=i

    i+=1
    # 60 day max RSI
    sheet.col(i).width = 5*367
    st = "RSI Max Min Diff"
    sheet.write(0, i, st, style_wrap)
    conf.RSI_DIFF=i

    i+=1
    # 60 day max RSI
    sheet.col(i).width = 8*367
    st = "RSI Range"
    sheet.write(0, i, st, style_wrap)
    conf.RSI_60_MAX=i

    i+=1
    # RSI min max price change
    sheet.col(i).width = 7*367
    st = "RSI price change"
    sheet.write(0, i, st, style_wrap)
    conf.RSI_PRICE_CHANGE=i

    i+=1
    # RSI min max price change
    sheet.col(i).width = 4*367
    st = "RSI price change days"
    sheet.write(0, i, st, style_wrap)
    conf.RSI_PRICE_CHANGE_DAYS=i

    i+=1
    # BBands 
    sheet.col(i).width = 8*367
    st = "BBands Range"
    sheet.write(0, i, st, style_wrap)
    conf.BBANDS_RANGE=i

    i+=1
    # Morning Star
    sheet.col(i).width = 3*367
    st = "MStar"
    sheet.write(0, i, st, style_wrap)
    conf.MSTAR=i


    return i

def add_calc_header(sheet, i):
    ##EPS
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "EPS", style_wrap)
    #conf.EPS=i

    #i+=1
    ##DCF Price
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "DCF Price", style_wrap)
    #conf.DCF_PR=i

    #i+=1
    ##MoS @50% Price
    #sheet.col(i).width = 5*367
    ##mos = "MoS Price @%r" %(stk['num']['margin_of_safety'])
    #sheet.write(0, i, "MoS Price @50", style_wrap)
    #conf.MOS_PR=i

    #i+=1
    ##Sale Price
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Sale Price", style_wrap)
    #conf.SAL_PR=i

    #i+=1
    ##Return Rate @ Current Price
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Cur Price Ret Rate", style_wrap)
    #conf.CUR_RT=i

    #i+=1
    ##Return Rate @ MoS Price
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "MoS Price Ret Rate", style_wrap)
    #conf.MOS_RT=i
    return i

def add_figs_growth_header(sheet, i, years):
    # 10 yr Sales Growth
    sheet.col(i).width = 5*367
    st = "%s yr Sales Gr" %(years)
    sheet.write(0, i, st, style_wrap)
    conf.TEN_SAL=i

    i+=1
    # 10 yr Profit Growth
    sheet.col(i).width = 5*367
    st = "%s yr Profit Gr"%(years)
    sheet.write(0, i, st, style_wrap)
    conf.TEN_PR=i

    i+=1
    #10 yr Book Value Growth
    sheet.col(i).width = 5*367
    st = "%s yr Book Gr"%(years)
    sheet.write(0, i, st, style_wrap)
    conf.TEN_BK=i

    i+=1
    # 10 yr Cash Growth
    sheet.col(i).width = 5*367
    st = "%s yr Cash Gr"%(years)
    sheet.write(0, i, st, style_wrap)
    conf.TEN_CSH=i

#    i+=1
#    # 5 yr Sales Growth
#    sheet.col(i).width = 4*367
#    sheet.write(0, i, "5 yr Sales Gr", style_wrap)
#    conf.FIVE_SAL=i
#
#    i+=1
#    # 5 yr Profit Growth
#    sheet.col(i).width = 6*367
#    sheet.write(0, i, "5 yr Profit Gr", style_wrap)
#    conf.FIVE_PR=i
#
#    i+=1
#    # 5 yr Book Value Growth
#    sheet.col(i).width = 4*367
#    sheet.write(0, i, "5 yr Book Gr", style_wrap)
#    conf.FIVE_BK=i
#
#    i+=1
#    # 5 yr Cash Growth
#    sheet.col(i).width = 4*367
#    sheet.write(0, i, "5 yr Cash Gr", style_wrap)
#    conf.FIVE_CSH=i
#
#    i+=1
#    # 3 yr Sales Growth
#    sheet.col(i).width = 4*367
#    sheet.write(0, i, "3 yr Sales Gr", style_wrap)
#    conf.THREE_SAL=i
#
#    i+=1
#    # 3 yr Profit Growth
#    sheet.col(i).width = 6*367
#    sheet.write(0, i, "3 yr Profit Gr", style_wrap)
#    conf.THREE_PR=i
#
#    i+=1
#    # 3 yr Book Value Growth
#    sheet.col(i).width = 4*367
#    sheet.write(0, i, "3 yr Book Gr", style_wrap)
#    conf.THREE_BK=i
#
#    i+=1
#    # 3 yr Cash Growth
#    sheet.col(i).width = 4*367
#    sheet.write(0, i, "3 yr Cash Gr", style_wrap)
#    conf.THREE_CSH=i
    return i

def add_betas_header(sheet, i):

    # Recession 2007 Beta
    sheet.col(i).width = 4*367
    sheet.write(0, i, "2007 Beta", style_wrap)
    conf.R2007_BETA=i

    i+=1
    # 2007 alpha
    sheet.col(i).width = 5*367
    sheet.write(0, i, "2007 Alpha", style_wrap)
    conf.R2007_ALPHA=i

    i+=1
    # 2007 pure alpha
    sheet.col(i).width = 5*367
    sheet.write(0, i, "2007 Pure Alpha", style_wrap)
    conf.R2007_PURE_ALPHA=i

    i+=1
    # 2007 CAGR
    sheet.col(i).width = 5*367
    sheet.write(0, i, "2007 CAGR", style_wrap)
    conf.R2007_CAGR=i

    #i+=1
    ## 2007 Index CAGR
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "2007 Index CAGR", style_wrap)
    #conf.R2007_ICAGR=i

    #i+=1
    ## Whole Beta
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Whole Beta", style_wrap)
    #conf.W_BETA=i

    i+=1
    # Whole Alpha
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Whole Alpha", style_wrap)
    conf.W_ALPHA=i

    i+=1
    # Whole Pure Alpha
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Whole Pure Alpha", style_wrap)
    conf.W_PURE_ALPHA=i

    #i+=1
    ## Profit Margin
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Profit Mgn", style_wrap)
    #conf.PRF_M=i

    #i+=1
    ## RoE
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "RoE", style_wrap)
    #conf.ROE=i

    #i+=1
    ## RoA
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "RoA", style_wrap)
    #conf.ROA=i

    #i+=1
    ## RoCE
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "RoCE", style_wrap)
    #conf.ROCE=i

    #i+=1
    ## Dividend Yield
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "Div Yield", style_wrap)
    #conf.DIV=i

    #i+=1
    ## Dividend Payout Ratio
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "Div Payout", style_wrap)
    #conf.DIV_PAY=i
    return i



def add_ratios_header(sheet, i):
    # P/E
    sheet.col(i).width = 4*367
    sheet.write(0, i, "P/E", style_wrap)
    conf.PE=i
    i+=1
    # Forward P/E
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Fwd P/E", style_wrap)
    conf.F_PE=i

    #i+=1
    ## TTM P/E
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "TTM P/E", style_wrap)
    #conf.TTM_PE=i

    #i+=1
    ## DtoTE
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "DtoTE", style_wrap)
    #conf.DTOTE=i

    #i+=1
    ## Interest Coverage
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "Intr Covr", style_wrap)
    #conf.INT_C=i

    #i+=1
    ## Profit Margin
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Profit Mgn", style_wrap)
    #conf.PRF_M=i

    #i+=1
    ## RoE
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "RoE", style_wrap)
    #conf.ROE=i

    #i+=1
    ## RoA
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "RoA", style_wrap)
    #conf.ROA=i

    #i+=1
    ## RoCE
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "RoCE", style_wrap)
    #conf.ROCE=i

    #i+=1
    ## Dividend Yield
    #sheet.col(i).width = 6*367
    #sheet.write(0, i, "Div Yield", style_wrap)
    #conf.DIV=i

    #i+=1
    ## Dividend Payout Ratio
    #sheet.col(i).width = 6*367
    #sheet.write(0, i, "Div Payout", style_wrap)
    #conf.DIV_PAY=i
    return i

def add_dcf_header(sheets, years, prices_only=False):
    for k in sheets.keys():
        sheet = sheets[k]
        i=0
        i = add_basic_header(sheet, i)

        if prices_only is False:
            i+=1
            i = add_calc_header(sheet, i)

            i+=1
            #Years of Data
            sheet.col(i).width = 5*367
            sheet.write(0, i, "Years of Data", style_wrap)
            conf.YR_DAT=i

            i+=1
            #Price Years of Data
            sheet.col(i).width = 5*367
            sheet.write(0, i, "Price Years of Data", style_wrap)
            conf.PRICE_YR_DAT=i

        i+=1
        i = add_price_change_header(sheet, i, 'ALL')

        i+=1
        i = add_technicals(sheet, i)

        i+=1
        i = add_fundamentals(sheet, i)

        i+=1
        i = add_valuation(sheet,i)

        i+=1
        # Price Growth
        sheet.col(i).width = 5*367
        st = "%s yr Price Gr" %(years)
        sheet.write(0, i, st, style_wrap)
        conf.TEN_PRICE=i

        i+=1
        i = add_ratios_header(sheet, i)

        i+=1
        i = add_betas_header(sheet, i)

        i+=1
        i = add_figs_growth_header(sheet, i, years)

        #i+=1
        ## Float
        #sheet.col(i).width = 6*367
        #sheet.write(0, i, "Float", style_wrap)
        #conf.FLT=i

        i+=1
        # Float Percent
        sheet.col(i).width = 6*367
        sheet.write(0, i, "Float %", style_wrap)
        conf.FLT_PER=i

def add_fundamentals(sheet, i):

    sheet.col(i).width = 5*367
    sheet.write(0, i, "EPS", style_wrap)
    conf.EPS=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "EPS Estimage Cur Yr", style_wrap)
    conf.EPS_ESTIMATE_CUR_YR=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "EPS Estimate Nxt Yr", style_wrap)
    conf.EPS_ESTIMATE_NEXT_YR=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Revenue Per Share TTM", style_wrap)
    conf.RPS_TTM=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Profit Per Share TTM", style_wrap)
    conf.PPS_TTM=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Gross Profit TTM", style_wrap)
    conf.GROSS_PROFIT_TTM=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Profit Margin", style_wrap)
    conf.PROFIT_MARGIN=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Oper Margin TTM", style_wrap)
    conf.OPER_MARGIN_TTM=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Quarterly Revenue Growth YoY", style_wrap)
    conf.QUART_REV_GROWTH_YOY=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Quarterly Earnings Growth YoY", style_wrap)
    conf.QUART_EARNINGS_GROWTH_YOY=i

    i+=1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Div Yield", style_wrap)
    conf.DIV=i

    i+=1
    # Dividend Payout Ratio
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Div Payout", style_wrap)
    conf.DIV_PAY=i
 
    return i

def add_technicals(sheet, i):
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Short Ratio", style_wrap)
    conf.SHORT_RATIO=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Shares Float", style_wrap)
    conf.SHARES_FLOAT_PERCENT=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Short Percent Float", style_wrap)
    conf.SHORT_PERCENT_FLOAT=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Short Percent Outstanding", style_wrap)
    conf.SHORT_PERCENT_OUTSTANDING=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Short Prior Month", style_wrap)
    conf.SHORT_PRIOR_MONTH=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "WallSt Target Price", style_wrap)
    conf.WALLST_TARGET_PRICE=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Analyst Target Price", style_wrap)
    conf.ANALYST_TARGET_PRICE=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Rating", style_wrap)
    conf.ANALYST_RATING=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Strong Buy", style_wrap)
    conf.STRONG_BUY=i

    i+=1
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Strong Sell", style_wrap)
    conf.STRONG_SELL=i

    return i


def add_valuation(sheet, i):
    sheet.col(i).width = 4*367
    sheet.write(0, i, "PE", style_wrap)
    conf.PE=i

    i+=1
    sheet.col(i).width = 4*367
    sheet.write(0, i, "PB", style_wrap)
    conf.PB=i

    i+=1
    sheet.col(i).width = 4*367
    sheet.write(0, i, "PBMRQ", style_wrap)
    conf.PBMRQ=i

    i+=1
    sheet.col(i).width = 4*367
    sheet.write(0, i, "PSTTM", style_wrap)
    conf.PSTTM=i

    i+=1
    sheet.col(i).width = 4*367
    sheet.write(0, i, "PEG", style_wrap)
    conf.PEG=i

    i+=1
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Book Value", style_wrap)
    conf.BOOK=i

    i+=1
    # 2007 Percent Change
    sheet.col(i).width = 6*367
    sheet.write(0, i, "2007 Percent Change", style_wrap)
    conf.R2007_PER_CHG=i

    return i

def add_price_change_header(sheet, i, sheet_type):
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Since 2020 Recession", style_wrap)
    conf.R2020=i

    i+=1
    # 2007 Percent Change
    sheet.col(i).width = 6*367
    sheet.write(0, i, "2007 Percent Change", style_wrap)
    conf.R2007_PER_CHG=i

    i+=1
    # 2007 Percent Change
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Since Then Till Last Recession", style_wrap)
    conf.SINCE_LAST_PER_CHG=i

    #i = i + 1
    ## 2007 Index Percent Change
    #sheet.col(i).width = 7*367
    #sheet.write(0, i, "2007 Index Percent Change", style_wrap)
    #conf.R2007_IPER_CHG=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "One Month Volatility", style_wrap)
    conf.VOLATILITY=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "One Month Momentum", style_wrap)
    conf.ONE_MOMENTUM=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Three Months Momentum", style_wrap)
    conf.THREE_MOMENTUM=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Six Months Momentum", style_wrap)
    conf.SIX_MOMENTUM=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Day Price Change", style_wrap)
    conf.DAY_PR_CHANGE=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Week Price Change", style_wrap)
    conf.WEEK_PR_CHANGE=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Two Week Price Change", style_wrap)
    conf.TWO_WEEK_PR_CHANGE=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Mon Price Change", style_wrap)
    conf.MON_PR_CHANGE=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Qr Price Change", style_wrap)
    conf.QR_PR_CHANGE=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Half Yr Price Change", style_wrap)
    conf.HF_YR_PR_CHANGE=i

    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Yr Price Change", style_wrap)
    conf.YR_PR_CHANGE=i
 
    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Whole Price Change", style_wrap)
    conf.WH_PR_CHANGE=i

    return i


#    # Year Price Change
#    if sheet_type == 'YEAR':
#        sheet.col(i).width = 6*367
#        sheet.write(0, i, "Yr Price Change", style_wrap)
#        conf.YR_PR_CHANGE=i
#        return i
#
#    # Quarter Price Change
#    if sheet_type == 'QUARTER':
#        sheet.col(i).width = 6*367
#        sheet.write(0, i, "Qr Price Change", style_wrap)
#        conf.QR_PR_CHANGE=i
#        return i
#
#    # Month Price Change
#    if sheet_type == 'MONTH':
#        sheet.col(i).width = 6*367
#        sheet.write(0, i, "Mon Price Change", style_wrap)
#        conf.MON_PR_CHANGE=i
#        return i
#
#    # Week Price Change
#    if sheet_type == 'WEEK':
#        sheet.col(i).width = 6*367
#        sheet.write(0, i, "Week Price Change", style_wrap)
#        conf.WEEK_PR_CHANGE=i
#        return i
#
#    # DAY Price Change
#    if sheet_type == 'DAY':
#        sheet.col(i).width = 8*367
#        sheet.write(0, i, "Day Price Change", style_wrap)
#        conf.DAY_PR_CHANGE=i
#        return i

def add_price_surprise_header(sheet, sheet_type):
    years=""
    i = 0
    i = add_basic_header(sheet, i)

    i+=1
    i = add_price_change_header(sheet, i, sheet_type)

    #i+=1
    #i = add_calc_header(sheet, i)

    #i+=1
    ##Years of Data
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Years of Data", style_wrap)
    #conf.YR_DAT=i

    #i+=1
    ##Price Years of Data
    #sheet.col(i).width = 5*367
    #sheet.write(0, i, "Price Years of Data", style_wrap)
    #conf.PRICE_YR_DAT=i

    i+=1
    # Price Growth
    sheet.col(i).width = 5*367
    st = "Price Gr"
    sheet.write(0, i, st, style_wrap)
    conf.TEN_PRICE=i

    i+=1
    i = add_figs_growth_header(sheet, i, years)

    i+=1
    i = add_ratios_header(sheet, i)

    i+=1
    # Float
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Float", style_wrap)
    conf.FLT=i

    i+=1
    # Float Percent
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Float %", style_wrap)
    conf.FLT_PER=i


def write_to_price_change_excel(count, ash, stk, sheet_type, prices_only=False):

    #DB.clear_dict(stk)

    if not isinstance(stk['num']['eps_20yr'], list):
        db=DB.open_db('Stocks')
        db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"num.eps_20yr":[]}})
        print("Setting eps_20yr to []")
        stk['num']['eps_20yr']=[]


#    if sheet_type == 'YEAR':
#        sh_write(ash, count, conf.YR_PR_CHANGE, stk['price_change']['year'], style_percent)
#    if sheet_type == 'QUARTER':
#        sh_write(ash, count, conf.QR_PR_CHANGE, stk['price_change']['quarter'], style_percent)
#    if sheet_type == 'MONTH':
#        sh_write(ash, count, conf.MON_PR_CHANGE, stk['price_change']['month'], style_percent)
#    if sheet_type == 'WEEK':
#        sh_write(ash, count, conf.WEEK_PR_CHANGE, stk['price_change']['week'], style_percent)
#    if sheet_type == 'DAY':
#        sh_write(ash, count, conf.DAY_PR_CHANGE, stk['price_change']['day'], style_percent)

    if stk['technicals']['rsi'] is not None and len(stk['technicals']['rsi'].keys()) > 0:
        sh_write(ash, conf.COUNT, conf.RSI, stk['technicals']['rsi']['latest'], style_decimal)
        sh_write(ash, conf.COUNT, conf.RSI_MIN_DIFF, (stk['technicals']['rsi']['latest'] - stk['technicals']['rsi']['60day_min']), style_decimal)
        sh_write(ash, conf.COUNT, conf.RSI_MAX_DIFF, (stk['technicals']['rsi']['60day_max'] - stk['technicals']['rsi']['latest']), style_decimal)
        sh_write(ash, conf.COUNT, conf.RSI_60_MAX, "{}-{}".format(round(stk['technicals']['rsi']['60day_min'],2), round(stk['technicals']['rsi']['60day_max'],2)), style_text)
        sh_write(ash, conf.COUNT, conf.RSI_DIFF, round(stk['technicals']['rsi']['60day_max'] - stk['technicals']['rsi']['60day_min'],2), style_decimal)
        if stk['technicals']['rsi']['60day_min_price_date'] < stk['technicals']['rsi']['60day_max_price_date']:
            rsi_price_change = percent_change(stk['technicals']['rsi']['60day_min_price'], stk['technicals']['rsi']['60day_max_price'])
        else:
            rsi_price_change = percent_change(stk['technicals']['rsi']['60day_max_price'], stk['technicals']['rsi']['60day_min_price'])
        sh_write(ash, conf.COUNT, conf.RSI_PRICE_CHANGE, rsi_price_change, style_percent)
        days = (stk['technicals']['rsi']['60day_max_price_date'] - stk['technicals']['rsi']['60day_min_price_date']).days
        sh_write(ash, conf.COUNT, conf.RSI_PRICE_CHANGE_DAYS, days, style_highlight)

    if stk['technicals']['bbands'] is not None and len(stk['technicals']['bbands'].keys()) > 0:
        sh_write(ash, conf.COUNT, conf.BBANDS_RANGE, "{}-{}".format(round(stk['technicals']['bbands']['lower'],2), round(stk['technicals']['bbands']['upper'],2)), style_text)
    
    if stk['technicals']['candlesticks'] is not None and stk['technicals']['candlesticks']['MORNINGSTAR'] != 0:
        sh_write(ash, conf.COUNT, conf.MSTAR, stk['technicals']['candlesticks']['MORNINGSTAR'], style_text)
 
    if stk['price_change']['whole'] is not None and stk['price_change']['whole'] != 0:
        sh_write(ash, count, conf.WH_PR_CHANGE, stk['price_change']['whole']/100, style_percent)
    sh_write(ash, count, conf.YR_PR_CHANGE, stk['price_change']['year'], style_percent)
    sh_write(ash, count, conf.HF_YR_PR_CHANGE, stk['price_change']['half_year'], style_percent)
    sh_write(ash, count, conf.QR_PR_CHANGE, stk['price_change']['quarter'], style_percent)
    sh_write(ash, count, conf.MON_PR_CHANGE, stk['price_change']['month'], style_percent)
    sh_write(ash, count, conf.WEEK_PR_CHANGE, stk['price_change']['week'], style_percent)
    sh_write(ash, count, conf.TWO_WEEK_PR_CHANGE, stk['price_change']['two_week'], style_percent)
    sh_write(ash, count, conf.DAY_PR_CHANGE, stk['price_change']['day'], style_percent)
    if 'betas' in stk['fig'].keys() and stk['fig']['betas']['one_month'] is not None:
        sh_write(ash, count, conf.VOLATILITY, stk['fig']['betas']['one_month']['volatility'], style_percent)
        sh_write(ash, count, conf.ONE_MOMENTUM, stk['fig']['betas']['one_month']['momentum'], style_percent)
        sh_write(ash, count, conf.THREE_MOMENTUM, stk['fig']['betas']['three_months']['momentum'], style_percent)
        sh_write(ash, count, conf.SIX_MOMENTUM, stk['fig']['betas']['six_months']['momentum'], style_percent)

    sh_write(ash, count, conf.COMP, stk['bscs']['name'], style_text)
    #sh_write(ash, count, conf.PRM_S, stk['bscs']['promoter_stake']/100, style_percent)
    #sh_write(ash, count, conf.FII, stk['bscs']['fii_stake']/100, style_percent)
    #sh_write(ash, count, conf.DII, stk['bscs']['dii_stake']/100, style_percent)
    sh_write(ash, count, conf.DIV, stk['Dividend']['yld']/100, style_percent)
    sh_write(ash, count, conf.DIV_PAY, stk['Dividend']['payout_ratio']/100, style_percent)
    sh_write(ash, count, conf.FLT, stk['bscs']['float']/100)
    try:
        sh_write(ash, count, conf.FLT_PER, stk['bscs']['float_percent']/100, style_percent)
    except Exception:
        pass

    sh_write(ash, count, conf.SYM, stk['bscs']['symbol'], style_text)
    sh_write(ash, count, conf.SEC, stk['General']['Sector'], style_text)
    sh_write(ash, count, conf.IND, stk['General']['GicSubIndustry'], style_text)
    sh_write(ash, count, conf.MCAP, stk['bscs']['marketCap'], style_num)
    #sh_write(ash, count, conf.REVENUE, get_latest_figure(stk, 'income-statement', 'Sales'), style_num)
    sh_write(ash, count, conf.SINCE, stk['bscs']['since'], style_text)
    sh_write(ash, count, conf.CUR_PR_DT, str(stk['bscs']['price_date']).split(' ')[0])
    sh_write(ash, count, conf.CUR_PR, stk['bscs']['regularMarketPrice'])
    sh_write(ash, count, conf.FIFTY_DAY_MA, stk['Technicals']['50DayMA'])
    sh_write(ash, count, conf.TWO_HUNDRED_DAY_MA, stk['Technicals']['200DayMA'])
    sh_write(ash, count, conf.F2WK_HG, stk['bscs']['fiftytwoweek_high'])
    sh_write(ash, count, conf.F2WK_LW, stk['bscs']['fiftytwoweek_low'])
    sh_write(ash, count, conf.W_F2WK_HG, stk['price_change']['with_52week_high'], style_percent)
    sh_write(ash, count, conf.W_F2WK_LW, stk['price_change']['with_52week_low'], style_percent)

    sh_write(ash, count, conf.VOL, stk['bscs']['volume'], style_num)
    if 'betas' in stk['fig'].keys() and stk['fig']['betas'] != None:
        sh_write(ash, count, conf.ONE_BETA, stk['fig']['betas']['one_month']['beta'])
        sh_write(ash, count, conf.THREE_BETA, stk['fig']['betas']['three_months']['beta'])
        sh_write(ash, count, conf.SIX_BETA, stk['fig']['betas']['six_months']['beta'])
        sh_write(ash, count, conf.YEAR_BETA, stk['fig']['betas']['one_year']['beta'])
        sh_write(ash, count, conf.FIVE_BETA, stk['fig']['betas']['five_year']['beta'])
        #sh_write(ash, count, conf.BETA, stk['bscs']['five_yr_beta'])

    sh_write(ash, count, conf.FV, stk['bscs']['face_value'])

    sh_write(ash, count, conf.PE, stk['Valuation']['TrailingPE'])
    sh_write(ash, count, conf.F_PE, stk['Valuation']['ForwardPE'])
    if stk['Highlights']['BookValue'] != 0:
        sh_write(ash, count, conf.PB, stk['price_change']['price']/stk['Highlights']['BookValue'])
    else:
        sh_write(ash, count, conf.PB, None)
    sh_write(ash, count, conf.PBMRQ, stk['Valuation']['PriceBookMRQ'])
    sh_write(ash, count, conf.PSTTM, stk['Valuation']['PriceSalesTTM'])
    sh_write(ash, count, conf.PEG, stk['Highlights']['PEGRatio'])
    sh_write(ash, count, conf.BOOK, stk['Highlights']['BookValue'])
    #sh_write(ash, count, conf.TTM_PE, stk['Ratios']['ttm_PE'])

    sh_write(ash, count, conf.SHORT_RATIO, stk['SharesStats']['ShortRatio'])
    sh_write(ash, count, conf.SHARES_FLOAT_PERCENT, stk['SharesStats']['SharesFloat']/ stk['SharesStats']['SharesOutstanding'])
    sh_write(ash, count, conf.SHORT_PERCENT_FLOAT, stk['SharesStats']['ShortPercentFloat'])
    sh_write(ash, count, conf.SHORT_PERCENT_OUTSTANDING, stk['SharesStats']['ShortPercentOutstanding'])
    sh_write(ash, count, conf.SHORT_PRIOR, stk['SharesStats']['SharesShortPriorMonth']/stk['SharesStats']['SharesOutstanding'])
    sh_write(ash, count, conf.WALLST_TARGET_PRICE, stk['Highlights']['WallStreetTargetPrice'])
    sh_write(ash, count, conf.ANALYST_TARGET_PRICE, stk['AnalystRatings']['TargetPrice'])
    sh_write(ash, count, conf.ANALYST_RATING, stk['AnalystRatings']['Rating'])
    sh_write(ash, count, conf.STRONG_BUY, stk['AnalystRatings']['StrongBuy'])
    sh_write(ash, count, conf.STRONG_SELL, stk['AnalystRatings']['StrongSell'])
 
    if prices_only == False:
        sh_write(ash, count, conf.YR_DAT, stk['num']['dcf_years'])
        #sh_write(ash, count, conf.PRICE_YR_DAT, stk['bscs']['price_years'])
        sh_write(ash, count, conf.SAL_PR, round(sum(stk['num']['eps_20yr']),2), style_decimal)
        sh_write(ash, count, conf.DCF_PR, stk['num']['dcf_price']*2, style_decimal)
        sh_write(ash, count, conf.MOS_PR, stk['num']['dcf_price'], style_decimal)
        sh_write(ash, count, conf.CUR_RT, stk['num']['cp_return_rate'], style_percent)
        sh_write(ash, count, conf.MOS_RT, stk['num']['dcf_return_rate'], style_percent)

        sh_write(ash, count, conf.EPS, stk['Highlights']['EarningsShare'], style_decimal)
        sh_write(ash, count, conf.EPS_ESTIMATE_CUR_YR, stk['Highlights']['EPSEstimateCurrentYear'], style_decimal)
        sh_write(ash, count, conf.EPS_ESTIMATE_NEXT_YR, stk['Highlights']['EPSEstimateNextYear'], style_decimal)
        sh_write(ash, count, conf.RPS_TTM, stk['Highlights']['RevenuePerShareTTM'], style_decimal)
        sh_write(ash, count, conf.PPS_TTM, stk['Highlights']['GrossProfitTTM']/ stk['SharesStats']['SharesOutstanding'], style_decimal)
        sh_write(ash, count, conf.GROSS_PROFIT, stk['Highlights']['GrossProfitTTM'], style_decimal)
        sh_write(ash, count, conf.PROFIT_MARGIN, stk['Highlights']['ProfitMargin'], style_decimal)
        sh_write(ash, count, conf.OPER_MARGIN_TTM, stk['Highlights']['OperatingMarginTTM'], style_decimal)
        sh_write(ash, count, conf.DIV, stk['SplitsDividends']['SplitsDividends'], style_percent)
        sh_write(ash, count, conf.DIV_PAY, stk['SplitsDividends']['PayoutRatio'], style_decimal)


    if len(stk['fig']['DtoE']) > 0:
        sh_write(ash, count, conf.DTOTE, stk['fig']['DtoE'][-1])
    else:
        sh_write(ash, count, conf.DTOTE, "-")
    # vpetla. Calcuate interest coverage ratio and uncomment this line
    ##sh_write(ash, count, conf.INT_C, stk['fig']['INTR'][-1])
    if len(stk['fig']['ROE']) > 0:
        sh_write(ash, count, conf.ROE, stk['fig']['ROE'][-1], style_percent)
    else:
        sh_write(ash, count, conf.ROE, "-")
    if len(stk['fig']['ROA']) > 0:
        sh_write(ash, count, conf.ROA, stk['fig']['ROA'][-1], style_percent)
    else:
        sh_write(ash, count, conf.ROA, "-")
    # vpetla. Calcuate ROCE and uncomment this line
    ##sh_write(ash, count, conf.ROCE, stk['fig']['ROCE'][-1])
    try:
        sh_write(ash, count, conf.PRF_M, stk['fig']['PAT_M'][-1]/100, style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        sh_write(ash, count, conf.TEN_PRICE, stk['fig']['price_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        sh_write(ash, count, conf.TEN_SAL, stk['fig']['sales_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        sh_write(ash, count, conf.TEN_PR, stk['fig']['profit_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        sh_write(ash, count, conf.TEN_BK, stk['fig']['book_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        sh_write(ash, count, conf.TEN_CSH, stk['fig']['cash_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))

def check_and_write(ash, count, col, entry, index, factor, style):
    if len(entry) > 0:
        sh_write(ash, count, col, entry[index]*factor, style)
    else:
        sh_write(ash, count, col, 0, style)

#com : Company Work Book
#ash : All Stocks Work Sheet
#stk : Stock information
def write_to_excel(country, com, ashs, stk, years, prices_only=False, radar_stocks=False, pp_stocks=False):
    #wb = xlwt.Workbook()

    try:
        #if not isinstance(stk['num']['eps_20yr'], list):
        if 'num' in stk.keys() and 'eps_20yr' not in stk['num'].keys():
            db=DB.open_db('Stocks')
            db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"num.eps_20yr":[]}})
            print("Setting eps_20yr to []")
            stk['num']['eps_20yr']=[]
    except Exception as e:
        print(str(e))

    if country == 'US':
        Mn = 1000000
        Bn = 1000*Mn
        Tn = 1000*Bn
        try:
            if radar_stocks:
                ash = ashs['Radar_Stocks']
            elif pp_stocks:
                ash = ashs['Portfolio_Stocks']
            elif stk['Highlights']['MarketCapitalization'] > 100 * Bn:
                ash = ashs['Above_100bn']
            elif stk['Highlights']['MarketCapitalization'] > 50 * Bn:
                ash = ashs['50bn_100bn']
            elif stk['Highlights']['MarketCapitalization'] > 25 * Bn:
                ash = ashs['25bn_50bn']
            elif stk['Highlights']['MarketCapitalization'] > 10 * Bn:
                ash = ashs['10bn_25bn']
            elif stk['Highlights']['MarketCapitalization'] > 5 * Bn:
                ash = ashs['5bn_10bn']
            elif stk['Highlights']['MarketCapitalization'] > 1 * Bn:
                ash = ashs['1bn_5bn']
            elif stk['Highlights']['MarketCapitalization'] > 500 * Mn:
                ash = ashs['500mn_1bn']
            elif stk['Highlights']['MarketCapitalization'] > 250 * Mn:
                ash = ashs['250mn_500mn']
            else:
                ash = ashs['Below_250mn']
            all_sht = ashs['All']
        except Exception as e:
            print("Mcap exception: %r" %(stk['bscs']['symbol']))
            return None

    #elif country == 'India':
    #    Bn = 100 # crores
    #    Tn = 100 * Bn
    #    if stk['bscs']['marketCap'] > 100 * Bn:
    #        ash = ashs{'Above_100bn'}
    #    elif stk['bscs']['marketCap'] > 10 * Bn:
    #        ash = ashs{'10bn_100bn'} 
    #    elif stk['bscs']['marketCap'] > 5 * Bn:
    #        ash = ashs{'5bn_10bn'}
    #    elif stk['bscs']['marketCap'] > 5 * Bn:
    #        ash = ashs{'1bn_5bn'}
    #    elif stk['bscs']['marketCap'] > 5 * Bn:
    #        ash = ashs{'Below_1bn'}

    conf.COUNT = len(ash.rows)
    #open a company sheet
    if radar_stocks:
        sheet = com.add_sheet("radar_dummy")
    elif pp_stocks:
        sheet = com.add_sheet("pp_dummy")
    else:
        sheet = com.add_sheet(stk['bscs']['symbol'])
    sheet.col(0).width = 28*367
    sheet.col(1).width = 10*367
    sheet.col(3).width = 10*367

    if 'dii_stake' in stk['bscs'].keys() and not stk['bscs']['dii_stake']:
        stk['bscs']['dii_stake']=0
    if 'Dividend' not in stk.keys() or 'yld' not in stk['Dividend'].keys():
        db=DB.open_db('Stocks')
        db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"Dividend.yld":0}})
        db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"Dividend.payout_ratio":0}})
        if 'Dividend' not in stk.keys():
            stk['Dividend'] = {}

        stk['Dividend']['yld']=0
        stk['Dividend']['payout_ratio']=0
    if 'Ratios' not in stk.keys() or 'interest_coverage' not in stk['Ratios'].keys():
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.interest_coverage", 0)
        if 'Ratios' not in stk.keys():
            stk['Ratios'] = {}
        stk['Ratios']['interest_coverage']=0
    if 'Ratios' not in stk.keys() or 'forward_PE' not in stk['Ratios'].keys():
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.forward_PE", 0)
        stk['Ratios']['forward_PE']=0
    if 'Ratios' not in stk.keys() or 'ttm_PE' not in stk['Ratios'].keys():
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.ttm_PE", 0)
        stk['Ratios']['ttm_PE']=0
    if 'float' not in stk['bscs'].keys():
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.float", 0)
        stk['bscs']['float'] = 0
    if 'float_percent' not in stk['bscs'].keys() or stk['bscs']['float_percent'] is None:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.float_percent", 0)
        stk['bscs']['float_percent'] = 0

    i = 0
    sheet.write(i, 0, "Date", style_bold)
    sheet.write(i, 1, arrow.now().format('DD-MM-YYYY'))
    #sheet.write(0, 1, str(date.today()))

    i = 2
    sheet.write(i, 0, "Basics")

    i += 1 #row 4
    sheet.write(i, 0, "Name")
    sheet.write(i, 1, stk['General']['Name'])
    sh_write(ash, conf.COUNT, conf.COMP, stk['General']['Name'], style_text, all_sht)

    sheet.write(i, 3, "Promoter Stake")
    if 'promoter_stake' in stk['bscs'].keys():
        sheet.write(i, 4, stk['bscs']['promoter_stake']/100, style_percent)
    #sh_write(ash, conf.COUNT, conf.PRM_S, stk['bscs']['promoter_stake']/100, style_percent, all_sht)
    #if 'fii_stake' in stk['bscs'].keys():
    #    sh_write(ash, conf.COUNT, conf.FII, stk['bscs']['fii_stake']/100, style_percent, all_sht)
    #if 'dii_stake' in stk['bscs'].keys():
    #    sh_write(ash, conf.COUNT, conf.DII, stk['bscs']['dii_stake']/100, style_percent, all_sht)

    sh_write(ash, conf.COUNT, conf.DIV, stk['Highlights']['DividendYield'], style_percent, all_sht)
    sh_write(ash, conf.COUNT, conf.DIV_PAY, stk['SplitsDividends']['PayoutRatio'], style_percent, all_sht)
   
    #Betas
    if 'fig' in stk.keys() and 'betas' in stk['fig'].keys() and stk['fig']['betas'] != None:
        if 'recession' in stk['fig']['betas'].keys() and stk['fig']['betas']['recession'] != None:
            if '2020' in stk['fig']['betas']['recession'].keys() and stk['fig']['betas']['recession']['2020'] != None:
                if 'Percent_Change' in stk['fig']['betas']['since_last_recession'].keys():
                    sh_write(ash, conf.COUNT, conf.R2020, stk['fig']['betas']['since_last_recession']['Percent_Change'], style_percent, all_sht)
            if '2007' in stk['fig']['betas']['recession'].keys():
                if stk['fig']['betas']['recession']['2007'] != None:
                    try:
                        sh_write(ash, conf.COUNT, conf.R2007_BETA, round(stk['fig']['betas']['recession']['2007']['beta'], 2), style_decimal, all_sht)
                        sh_write(ash, conf.COUNT, conf.R2007_ALPHA, round(stk['fig']['betas']['recession']['2007']['alpha'], 2), style_decimal, all_sht)
                        sh_write(ash, conf.COUNT, conf.R2007_PURE_ALPHA, round(stk['fig']['betas']['recession']['2007']['alpha_pure'], 2), style_decimal, all_sht)
                        #sh_write(ash, conf.COUNT, conf.R2007_IPER_CHG, round(stk['fig']['betas']['recession']['2007']['Index_Percent_Change'], 2), style_percent, all_sht)
                        sh_write(ash, conf.COUNT, conf.R2007_PER_CHG, round(stk['fig']['betas']['recession']['2007']['Percent_Change'], 2), style_percent, all_sht)
                        sh_write(ash, conf.COUNT, conf.R2007_CAGR, round(stk['fig']['betas']['recession']['2007']['CAGR'], 2), style_decimal, all_sht)
                        #sh_write(ash, conf.COUNT, conf.R2007_ICAGR, round(stk['fig']['betas']['recession']['2007']['Index_CAGR'], 2), style_decimal, all_sht)
                        sh_write(ash, conf.COUNT, conf.SINCE_LAST_PER_CHG, round(stk['fig']['betas']['recession']['2007']['since_then_till_last_recession'], 2), style_decimal, all_sht)
                    except Exception:
                        pass
        if 'whole' in stk['fig']['betas'].keys() and stk['fig']['betas']['whole']:
            sh_write(ash, conf.COUNT, conf.W_BETA, round(stk['fig']['betas']['whole']['beta'], 2), style_decimal, all_sht)
            sh_write(ash, conf.COUNT, conf.W_ALPHA, round(stk['fig']['betas']['whole']['alpha'], 2), style_decimal, all_sht)
            sh_write(ash, conf.COUNT, conf.W_PURE_ALPHA, round(stk['fig']['betas']['whole']['alpha_pure'], 2), style_decimal, all_sht)

        if 'one_month' in stk['fig']['betas'].keys() and stk['fig']['betas']['one_month']:
            sh_write(ash, conf.COUNT, conf.ONE_BETA,  round(stk['fig']['betas']['one_month']['beta'],2), all_sht=all_sht)
        if 'three_months' in stk['fig']['betas'].keys() and stk['fig']['betas']['three_months']:
            sh_write(ash, conf.COUNT, conf.THREE_BETA,  round(stk['fig']['betas']['three_months']['beta'],2), all_sht=all_sht)
        if 'six_months' in stk['fig']['betas'].keys() and stk['fig']['betas']['six_months']:
            sh_write(ash, conf.COUNT, conf.SIX_BETA,  round(stk['fig']['betas']['six_months']['beta'],2), all_sht=all_sht)
        if 'one_year' in stk['fig']['betas'].keys() and stk['fig']['betas']['one_year']:
            sh_write(ash, conf.COUNT, conf.YEAR_BETA, round(stk['fig']['betas']['one_year']['beta'],2), all_sht=all_sht)
        if 'five_year' in stk['fig']['betas'].keys() and stk['fig']['betas']['five_year']:
            sh_write(ash, conf.COUNT, conf.FIVE_BETA, round(stk['fig']['betas']['five_year']['beta'],2), all_sht=all_sht)

    if stk['SharesStats']['SharesOutstanding'] == 0:
        float_percent = 0
    else:
        float_percent = stk['SharesStats']['SharesFloat']/stk['SharesStats']['SharesOutstanding']
    sh_write(ash, conf.COUNT, conf.FLT_PER, float_percent, style_percent, all_sht)

    i += 1 #row 5
    sheet.write(i, 0, "Symbol")
    sheet.write(i, 1, stk['bscs']['symbol'])
    sh_write(ash, conf.COUNT, conf.SYM, stk['bscs']['symbol'], style_text, all_sht)
    sh_write(ash, conf.COUNT, conf.SEC, stk['General']['Sector'], style_text, all_sht)
    sh_write(ash, conf.COUNT, conf.IND, stk['General']['GicSubIndustry'], style_text, all_sht)
    sh_write(ash, conf.COUNT, conf.SINCE, stk['General']['IPODate'], style_text, all_sht)

    sheet.write(i, 3, "Public Stake")
    if 'pub_stake' in stk['bscs'].keys():
        sheet.write(i, 4, stk['bscs']['pub_stake']/100, style_percent)
    
    if 'price' in stk['bscs'].keys():
        stk['bscs']['regularMarketPrice'] = stk['bscs']['price']
    i += 1 #row 6
    sheet.write(i, 0, "Price")
    if 'price' in stk['price_change'].keys():
        sheet.write(i, 1, stk['price_change']['price'])
    sh_write(ash, conf.COUNT, conf.CUR_PR_DT, str(stk['price_change']['date']).split(' ')[0], all_sht=all_sht)
    if 'price' in stk['price_change'].keys():
        sh_write(ash, conf.COUNT, conf.CUR_PR, stk['price_change']['price'], style_decimal, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.FIFTY_DAY_MA, stk['Technicals']['50DayMA'], style_decimal, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.TWO_HUNDRED_DAY_MA, stk['Technicals']['200DayMA'], style_decimal, all_sht=all_sht)
    if 'fiftytwoweek_high' in stk['bscs'].keys():
        sh_write(ash, conf.COUNT, conf.F2WK_HG, stk['bscs']['fiftytwoweek_high'], all_sht=all_sht)
    if 'fiftytwoweek_low' in stk['bscs'].keys():
        sh_write(ash, conf.COUNT, conf.F2WK_LW, stk['bscs']['fiftytwoweek_low'], all_sht=all_sht)
    if 'with_52week_high' in stk['price_change'].keys():
        sh_write(ash, conf.COUNT, conf.W_F2WK_HG, stk['price_change']['with_52week_high'], style_percent, all_sht)
    if 'with_52week_low' in stk['price_change'].keys():
        sh_write(ash, conf.COUNT, conf.W_F2WK_LW, stk['price_change']['with_52week_low'], style_percent, all_sht)


    sheet.write(i, 3, "Volume")
    #sheet.write(i, 4, stk['price_change']['volume'])
    #sh_write(ash, conf.COUNT, conf.VOL, stk['price_change']['volume'], all_sht=all_sht)

    #i += 1 #row 7
    #sheet.write(i, 0, "Face Value")
    #if 'Face Value' in stk['bscs'].keys():
    #    sheet.write(i, 1, stk['bscs']['face_value'])
    #    sh_write(ash, conf.COUNT, conf.FV, stk['bscs']['face_value'], all_sht)

    sh_write(ash, conf.COUNT, conf.PE, stk['Valuation']['TrailingPE'], style_decimal, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.F_PE, stk['Valuation']['ForwardPE'], style_decimal, all_sht=all_sht)
    if stk['Highlights']['BookValue'] != None  and stk['Highlights']['BookValue'] > 0 and 'price' in stk['price_change'].keys():
        sh_write(ash, conf.COUNT, conf.PB, stk['price_change']['price']/stk['Highlights']['BookValue'], style_decimal, all_sht=all_sht)
    else:
        sh_write(ash, conf.COUNT, conf.PB, None, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.PBMRQ, stk['Valuation']['PriceBookMRQ'], style_decimal, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.PSTTM, stk['Valuation']['PriceSalesTTM'], style_decimal, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.PEG, stk['Highlights']['PEGRatio'], style_decimal, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.BOOK, stk['Highlights']['BookValue'], style_decimal, all_sht=all_sht)

    #sh_write(ash, conf.COUNT, conf.TTM_PE, stk['Ratios']['ttm_PE'], all_sht=all_sht)


    sh_write(ash, conf.COUNT, conf.SHORT_RATIO, stk['SharesStats']['ShortRatio'], style_decimal, all_sht=all_sht)

    try:
        if stk['SharesStats']['SharesOutstanding'] > 0:
            sh_write(ash, conf.COUNT, conf.SHARES_FLOAT_PERCENT, stk['SharesStats']['SharesFloat']/ stk['SharesStats']['SharesOutstanding'], style_percent, all_sht=all_sht)
            sh_write(ash, conf.COUNT, conf.SHORT_PRIOR_MONTH, stk['SharesStats']['SharesShortPriorMonth']/stk['SharesStats']['SharesOutstanding'], style_percent, all_sht=all_sht)
        sh_write(ash, conf.COUNT, conf.PPS_TTM, stk['Highlights']['GrossProfitTTM']/ stk['SharesStats']['SharesOutstanding'], style_decimal, all_sht)
    except Exception as E:
        print(stk['SharesStats'])

    sh_write(ash, conf.COUNT, conf.SHORT_PERCENT_FLOAT, stk['SharesStats']['ShortPercentFloat'], style_percent, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.SHORT_PERCENT_OUTSTANDING, stk['SharesStats']['ShortPercentOutstanding'], style_percent, all_sht=all_sht)
    sh_write(ash, conf.COUNT, conf.WALLST_TARGET_PRICE, stk['Highlights']['WallStreetTargetPrice'], style_decimal, all_sht=all_sht)

    if 'AnalystRatings' in stk.keys():
        sh_write(ash, conf.COUNT, conf.ANALYST_TARGET_PRICE, stk['AnalystRatings']['TargetPrice'], style_decimal, all_sht=all_sht)
        sh_write(ash, conf.COUNT, conf.ANALYST_RATING, stk['AnalystRatings']['Rating'], style_decimal, all_sht=all_sht)
        sh_write(ash, conf.COUNT, conf.STRONG_BUY, stk['AnalystRatings']['StrongBuy'], all_sht=all_sht)
        sh_write(ash, conf.COUNT, conf.STRONG_SELL, stk['AnalystRatings']['StrongSell'], all_sht=all_sht)
    
    if prices_only is False:
        i += 1
        sheet.write(i, 0, "Five Year Beta")
        sheet.write(i, 1, stk['bscs']['five_yr_beta'])
    #sh_write(ash, conf.COUNT, conf.BETA, stk['bscs']['five_yr_beta'], all_sht=all_sht)

    if prices_only is False:
        i = 10 #row 11
        sheet.write(i, 0, "Growth Rate(1-5 Years)")
        if 'num' in stk.keys():
            sheet.write(i, 1, stk['num']['growth_1to5'], style_percent)

        sheet.write(i, 4, "Book Value", style_bold)
        sheet.write(i, 5, "Sales", style_bold)
        sheet.write(i, 6, "Cash Flow", style_bold)
        sheet.write(i, 7, "PAT", style_bold)

        i += 1 #row 12
        sheet.write(i, 0, "Growth Rate(6-8 Years)")
        # TODO replace 0.7, 0.8 with variables.
        sheet.write(i, 1, Formula("B11 * 0.7"), style_percent)

        sheet.write(i, 3, "Years", style_bold)
        #sheet.write(i, 4, len(stk['fig']['BOOK']))
        #sheet.write(i, 5, len(stk['fig']['Sales']))
        #sheet.write(i, 6, len(stk['fig']['CASH']))
        #sheet.write(i, 7, len(stk['fig']['PAT']))
        #sh_write(ash, conf.COUNT, conf.YR_DAT, len(stk['fig']['Sales']), all_sht=all_sht)
        sheet.write(i, 4, years)
        sheet.write(i, 5, years)
        sheet.write(i, 6, years)
        sheet.write(i, 7, years)
        sh_write(ash, conf.COUNT, conf.YR_DAT, years, all_sht=all_sht)
        ##sh_write(ash, conf.COUNT, conf.PRICE_YR_DAT, stk['bscs']['price_years'], all_sht=all_sht)

        i += 1 #row 13
        #sheet.write(i, 0, "Growth Rate(9-10 Years)")
        #sheet.write(i, 1, Formula("B12 * 0.8"), style_percent)
        #sheet.write(i, 3, "Growth Rate", style_bold)
        #sheet.write(i, 4, stk['fig']['book_growth'], style_percent)
        #sheet.write(i, 5, stk['fig']['sales_growth'], style_percent)
        #sheet.write(i, 6, stk['fig']['cash_growth'], style_percent)
        #sheet.write(i, 7, stk['fig']['profit_growth'], style_percent)

        i += 1 #row 14
        sheet.write(i, 0, "Terminal Growth Rate(10-15 Years)")
        sheet.write(i, 1, Formula("B13 * 0.5"), style_percent)

        i += 1 #row 15
        sheet.write(i, 0, "Terminal Growth Rate(16-20 Years)")
        sheet.write(i, 1, Formula("B14 * 0.8"), style_percent)

        i += 1 #row 16
        sheet.write(i, 0, "Discount Rate")
        if 'num' in stk.keys():
            sheet.write(i, 1, stk['num']['discount_rate'], style_percent)

        i += 1 #row 17
        sheet.write(i, 0, "Inflation")
        if 'num' in stk.keys():
            sheet.write(i, 1, stk['num']['inflation'], style_percent)

        i += 1 #row 18
        sheet.write(i, 0, "Margin of Safety")
        if 'num' in stk.keys():
            sheet.write(i, 1, stk['num']['margin_of_safety'], style_percent)

        # Earning Calculation
        i = 21 #row 22
        sheet.write(i, 0, "Year")
        now = datetime.datetime.now()
        now = int(now.year) - 1 # Year 2018
        sheet.write(i, 1, now)

        i += 1 #row 23
        #sheet.write(i, 0, "EPS")
        #sheet.write(i, 1, stk['fig']['ttm_eps'])

        i += 1 #row 24
        sheet.write(i, 0, "Growth Value")
        for j in range(1,11):
            sheet.write(i, j, now+j, style_bold)

        i += 1 #row 25
        sheet.write(i, 1, Formula("$B$23 * ((1+$B$11)/(1+$B$16))"), style_decimal)
        sheet.write(i, 2, Formula("$B$25 * ((1+$B$11)/(1+$B$16))"), style_decimal)
        sheet.write(i, 3, Formula("$C$25 * ((1+$B$11)/(1+$B$16))"), style_decimal)
        sheet.write(i, 4, Formula("$D$25 * ((1+$B$11)/(1+$B$16))"), style_decimal)
        sheet.write(i, 5, Formula("$E$25 * ((1+$B$11)/(1+$B$16))"), style_decimal)
        sheet.write(i, 6, Formula("$F$25 * ((1+$B$12)/(1+$B$16))"), style_decimal)
        sheet.write(i, 7, Formula("$G$25 * ((1+$B$12)/(1+$B$16))"), style_decimal)
        sheet.write(i, 8, Formula("$H$25 * ((1+$B$12)/(1+$B$16))"), style_decimal)
        sheet.write(i, 9, Formula("$I$25 * ((1+$B$13)/(1+$B$16))"), style_decimal)
        sheet.write(i, 10, Formula("$J$25 * ((1+$B$13)/(1+$B$16))"), style_decimal)


        i +=2  #row 28
        sheet.write(i, 0, "Terminal Value")
        for j in range(11,21):
            sheet.write(i, j-10, now+j, style_bold)

        i += 1 #row 29
        sheet.write(i, 1, Formula("$K$25 * ((1+$B$14)/(1+$B$16))"), style_decimal)
        sheet.write(i, 2, Formula("$B$28 * ((1+$B$14)/(1+$B$16))"), style_decimal)
        sheet.write(i, 3, Formula("$C$28 * ((1+$B$14)/(1+$B$16))"), style_decimal)
        sheet.write(i, 4, Formula("$D$28 * ((1+$B$14)/(1+$B$16))"), style_decimal)
        sheet.write(i, 5, Formula("$E$28 * ((1+$B$14)/(1+$B$16))"), style_decimal)
        sheet.write(i, 6, Formula("$F$28 * ((1+$B$15)/(1+$B$16))"), style_decimal)
        sheet.write(i, 7, Formula("$G$28 * ((1+$B$15)/(1+$B$16))"), style_decimal)
        sheet.write(i, 8, Formula("$H$28 * ((1+$B$15)/(1+$B$16))"), style_decimal)
        sheet.write(i, 9, Formula("$I$28 * ((1+$B$15)/(1+$B$16))"), style_decimal)
        sheet.write(i, 10, Formula("$J$28 * ((1+$B$15)/(1+$B$16))"), style_decimal)

        i += 2 #row 32
        sheet.write(i, 0, "EPS by Year")

        # Earnings by 2024
        i += 1 #row 33
        now += 1 #2024
        yr = "%r" %(now + 5)
        sheet.write(i, 0, yr)
        sheet.write(i, 1, Formula("SUM($B$25:$F$25)"), style_decimal)

        # Earnings by 2029
        i += 1 #row 34
        yr = "%r" % (now + 10)
        sheet.write(i, 0, yr)
        sheet.write(i, 1, Formula("SUM($B$25:$K$25)"), style_decimal)

        #if 'num' in stk.keys():
        #    i += 1 #row 35
        #    yr = "EPS by %r at %r percent inflation" % (now + 5, (stk['num']['inflation'])*100)
        #    sheet.write(i, 0, yr)
        #    sheet.write(i, 1, Formula("$B$31 * ((1-$B$17)^5)"), style_decimal)

        #    i += 2 #row 36
        #    sheet.write(i, 0, "Earnings after 20 years")
        #    sheet.write(i, 1, Formula("SUM($B$25:$K$25) + SUM($B$28:$K$28)"), style_decimal)
        #    sh_write(ash, conf.COUNT, conf.SAL_PR, round(sum(stk['num']['eps_20yr']),2), style_decimal, all_sht=all_sht)

        #    i += 1 #row 37
        #    sheet.write(i, 0, "Today's Value with Inflation")
        #    sheet.write(i, 1, Formula("($B$35 * ((1-$B$17)^20)) * $B$9"), style_decimal, all_sht)
        #    sh_write(ash, conf.COUNT, conf.DCF_PR, stk['num']['dcf_price']*2, style_decimal, all_sht)
        #    sh_write(ash, conf.COUNT, conf.EPS, stk['fig']['ttm_eps'], style_decimal, all_sht)

        #    i += 1 #row 38
        #    sheet.write(i, 0, "Price with Margin of Safety")
        #    sheet.write(i, 1, Formula("$B$36*$B$18"), style_decimal)
        #    sh_write(ash, conf.COUNT, conf.MOS_PR, stk['num']['dcf_price'], style_decimal, all_sht)

        #    i += 1  # row 39
        #    sheet.write(i, 0, "Current Price", style_bold)
        #    sheet.write(i, 1, stk['bscs']['regularMarketPrice'], style_bold)
        #    sheet.write(i, 2, "Profit", style_bold)

        #    i += 1 #row 40
        #    sheet.write(i, 0, "Value of MoS Price after 20 years with inflation")
        #    sheet.write(i, 1, Formula("$B$37*((1+$B$17)^20)"), style_decimal)
        #    sheet.write(i, 2, Formula("$B$35-$B$38"), style_decimal)

        #    i += 1 #row 4
        #    sheet.write(i, 0, "Rate of return at Current Price")
        #    sheet.write(i, 1, Formula("($B$35/$B$38)^0.05-1"), style_percent)
        #    sh_write(ash, conf.COUNT, conf.CUR_RT, stk['num']['cp_return_rate'], style_percent, all_sht)
        #    #sheet.write(i, 1, Formula("((($B$35/$B$39)^(1/$K$27-$B$22))-1)))"), style_percent, all_sht)

        #    i += 1 #row 41
        #    sheet.write(i, 0, "Rate of return at MoS Price")
        #    sheet.write(i, 1, Formula("($B$35/$B$37)^0.05-1"), style_percent)
        #    sh_write(ash, conf.COUNT, conf.MOS_RT, stk['num']['dcf_return_rate'], style_percent, all_sht)

    #Fundamentals

    sh_write(ash, conf.COUNT, conf.EPS, stk['Highlights']['EarningsShare'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.EPS_ESTIMATE_CUR_YR, stk['Highlights']['EPSEstimateCurrentYear'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.EPS_ESTIMATE_NEXT_YR, stk['Highlights']['EPSEstimateNextYear'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.RPS_TTM, stk['Highlights']['RevenuePerShareTTM'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.GROSS_PROFIT_TTM, stk['Highlights']['GrossProfitTTM'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.PROFIT_MARGIN, stk['Highlights']['ProfitMargin'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.OPER_MARGIN_TTM, stk['Highlights']['OperatingMarginTTM'], style_decimal, all_sht)
    sh_write(ash, conf.COUNT, conf.DIV, stk['SplitsDividends']['ForwardAnnualDividendYield'], style_percent, all_sht)
    sh_write(ash, conf.COUNT, conf.DIV_PAY, stk['SplitsDividends']['PayoutRatio'], style_decimal, all_sht)


    #Ratios
    #if 'DtoE' in stk['fig'].keys():
    #    check_and_write(ash, conf.COUNT, conf.DTOTE, stk['fig']['DtoE'], -1, 1, style_num)
    # vpetla. Calcuate interest coverage ratio and uncomment this line
    ##sh_write(ash, conf.COUNT, conf.INT_C, stk['fig']['INTR'][-1], all_sht)
    #if 'ROE' in stk['fig'].keys():
    #    check_and_write(ash, conf.COUNT, conf.ROE, stk['fig']['ROE'], -1, 1, style_percent)
    #if 'ROA' in stk['fig'].keys():
    #    check_and_write(ash, conf.COUNT, conf.ROA, stk['fig']['ROA'], -1, 1, style_percent)
    ## vpetla. Calcuate ROCE and uncomment this line
    ###sh_write(ash, conf.COUNT, conf.ROCE, stk['fig']['ROCE'][-1], all_sht=all_sht)
    #if 'PAT_M' in stk['fig'].keys():
    #    check_and_write(ash, conf.COUNT, conf.PRF_M, stk['fig']['PAT_M'], -1, 1/100, style_percent)
    sh_write(ash, conf.COUNT, conf.MCAP, stk['Highlights']['MarketCapitalizationMln'], style_num, all_sht)
    #sh_write(ash, conf.COUNT, conf.REVENUE, get_latest_figure(stk, 'income-statement', 'Sales'), style_num, all_sht=all_sht)

    if stk['technicals']['rsi'] is not None and len(stk['technicals']['rsi'].keys()) > 0:
        sh_write(ash, conf.COUNT, conf.RSI, stk['technicals']['rsi']['latest'], style_decimal, all_sht)
        if '60day_min' in stk['technicals']['rsi'].keys():
            sh_write(ash, conf.COUNT, conf.RSI_MIN_DIFF, (stk['technicals']['rsi']['latest'] - stk['technicals']['rsi']['60day_min']), style_decimal, all_sht)
            sh_write(ash, conf.COUNT, conf.RSI_MAX_DIFF, (stk['technicals']['rsi']['60day_max'] - stk['technicals']['rsi']['latest']), style_decimal, all_sht)
            sh_write(ash, conf.COUNT, conf.RSI_60_MAX, "{}-{}".format(round(stk['technicals']['rsi']['60day_min'],2), round(stk['technicals']['rsi']['60day_max'],2)), style_text, all_sht)
            sh_write(ash, conf.COUNT, conf.RSI_DIFF, round(stk['technicals']['rsi']['60day_max'] - stk['technicals']['rsi']['60day_min'],2), style_decimal, all_sht)
            if stk['technicals']['rsi']['60day_min_price_date'] < stk['technicals']['rsi']['60day_max_price_date']:
                rsi_price_change = percent_change(stk['technicals']['rsi']['60day_min_price'], stk['technicals']['rsi']['60day_max_price'])
            else:
                rsi_price_change = percent_change(stk['technicals']['rsi']['60day_max_price'], stk['technicals']['rsi']['60day_min_price'])
            sh_write(ash, conf.COUNT, conf.RSI_PRICE_CHANGE, rsi_price_change, style_percent, all_sht)
            days = (stk['technicals']['rsi']['60day_max_price_date'] - stk['technicals']['rsi']['60day_min_price_date']).days
            sh_write(ash, conf.COUNT, conf.RSI_PRICE_CHANGE_DAYS, days, style_highlight, all_sht)

    if 'bbands' in stk['technicals'].keys() and stk['technicals']['bbands'] is not None and len(stk['technicals']['bbands'].keys()) > 0:
        sh_write(ash, conf.COUNT, conf.BBANDS_RANGE, "{}-{}".format(round(stk['technicals']['bbands']['lower'],2), round(stk['technicals']['bbands']['upper'],2)), style_text, all_sht)

    if 'candlesticks' in stk['technicals'].keys() and stk['technicals']['candlesticks'] is not None and 'MORNINGSTAR' in stk['technicals']['candlesticks'].keys() and stk['technicals']['candlesticks']['MORNINGSTAR'] != 0:
        sh_write(ash, conf.COUNT, conf.MSTAR, stk['technicals']['candlesticks']['MORNINGSTAR'], style_text, all_sht)

    if 'whole' in stk['price_change'].keys() and stk['price_change']['whole'] is not None and stk['price_change']['whole'] != 0:
        sh_write(ash, conf.COUNT, conf.WH_PR_CHANGE, stk['price_change']['whole']/100, style_percent, all_sht)
    if 'year' in stk['price_change'].keys() and stk['price_change']['year'] is not None and stk['price_change']['year'] != 0:
        sh_write(ash, conf.COUNT, conf.YR_PR_CHANGE, stk['price_change']['year'], style_percent, all_sht)
    if 'half_year' in stk['price_change'].keys() and stk['price_change']['half_year'] is not None and stk['price_change']['half_year'] != 0:
        sh_write(ash, conf.COUNT, conf.HF_YR_PR_CHANGE, stk['price_change']['half_year'], style_percent, all_sht)
    if 'quarter' in stk['price_change'].keys() and stk['price_change']['quarter'] is not None and stk['price_change']['quarter'] != 0:
        sh_write(ash, conf.COUNT, conf.QR_PR_CHANGE, stk['price_change']['quarter'], style_percent, all_sht)
    if 'month' in stk['price_change'].keys() and stk['price_change']['month'] is not None and stk['price_change']['month'] != 0:
        sh_write(ash, conf.COUNT, conf.MON_PR_CHANGE, stk['price_change']['month'], style_percent, all_sht)
    if 'week' in stk['price_change'].keys() and stk['price_change']['week'] is not None and stk['price_change']['week'] != 0:
        sh_write(ash, conf.COUNT, conf.WEEK_PR_CHANGE, stk['price_change']['week'], style_percent, all_sht)
    if 'two_week' in stk['price_change'].keys() and stk['price_change']['two_week'] is not None and stk['price_change']['two_week'] != 0:
        sh_write(ash, conf.COUNT, conf.TWO_WEEK_PR_CHANGE, stk['price_change']['two_week'], style_percent, all_sht)
    if 'day' in stk['price_change'].keys() and stk['price_change']['day'] is not None and stk['price_change']['day'] != 0:
        sh_write(ash, conf.COUNT, conf.DAY_PR_CHANGE, stk['price_change']['day'], style_percent, all_sht)

    if 'fig' in stk.keys():
        if 'betas' in stk['fig'].keys() and stk['fig']['betas']['one_month'] is not None:
            sh_write(ash, conf.COUNT, conf.VOLATILITY, stk['fig']['betas']['one_month']['volatility'], style_percent, all_sht)
            sh_write(ash, conf.COUNT, conf.ONE_MOMENTUM, stk['fig']['betas']['one_month']['momentum'], style_percent, all_sht)
            sh_write(ash, conf.COUNT, conf.THREE_MOMENTUM, stk['fig']['betas']['three_months']['momentum'], style_percent)
            sh_write(ash, conf.COUNT, conf.SIX_MOMENTUM, stk['fig']['betas']['six_months']['momentum'], style_percent)
 
        if 'price_growth' in stk['fig'].keys():
            sh_write(ash, conf.COUNT, conf.TEN_PRICE, stk['fig']['price_growth'], style_percent, all_sht)
        if 'sales_growth' in stk['fig'].keys():
            sh_write(ash, conf.COUNT, conf.TEN_SAL, stk['fig']['sales_growth'], style_percent, all_sht)
        if 'profit_growth' in stk['fig'].keys():
            sh_write(ash, conf.COUNT, conf.TEN_PR, stk['fig']['profit_growth'], style_percent, all_sht)
        if 'book_growth' in stk['fig'].keys():
            sh_write(ash, conf.COUNT, conf.TEN_BK, stk['fig']['book_growth'], style_percent, all_sht)
        if 'cash_growth' in stk['fig'].keys():
            sh_write(ash, conf.COUNT, conf.TEN_CSH, stk['fig']['cash_growth'], style_percent, all_sht)
    #sheet.write(i, 1, Formula("((($B$35/$B$37)^(1/$K$27-$B$22))-1)))"), style_percent, all_sht)
    return sheet

#    excel = "excel_files/%s.xls" %(stk['bscs']['name'])

#    PRINT("Writing to %s"%(excel))
#    wb.save(excel)


