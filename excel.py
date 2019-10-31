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
    if not index:
        entry.append(sym)
    entry.append(name)
    price = internet.get_LTP(country, sym)
    entry.append(str(price))
    if not index:
        entry.append(str(shortlist_price))
        since_shortlist = price / shortlist_price - 1  
        entry.append(str(round(since_shortlist*100, 2))+'%')

    change = None
    try:
        if index:
            change,diff = internet.index_change(country, sym, name, 2, 'HOT')
            entry.append(str(round(diff,2)))
        else:
            change = internet.price_change(country, sym, name, 2, 'HOT')
        entry.append(str(round(change*100, 2))+'%')
        change = internet.price_change(country, sym, name, 7, 'HOT')
        entry.append(str(round(change*100, 2))+'%')
        change = internet.price_change(country, sym, name, 30, 'HOT')
        entry.append(str(round(change*100, 2))+'%')
        change = internet.price_change(country, sym, name, 90, 'HOT')
        entry.append(str(round(change*100, 2))+'%')
        change = internet.price_change(country, sym, name, 180, 'HOT')
        entry.append(str(round(change*100, 2))+'%')
        change = internet.price_change(country, sym, name, 365, 'HOT')
        entry.append(str(round(change*100, 2))+'%')
        if index:
            change = internet.price_change(country, sym, name, 365*5, 'HOT')
            entry.append(str(round(change*100, 2))+'%')
            change = internet.price_change(country, sym, name, 365*10, 'HOT')
            if change:
                entry.append(str(round(change*100, 2))+'%')
    except Exception as e:
        print(change)
        sys.exit()
    #print(entry)
    return entry
 
def get_radar_stocks():
    wb = xlrd.open_workbook('US_Stocks/DCF_Calc/radar_stocks.xls')
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
    entries.append(get_symbol_prices("^BSESN", "BSE", 'US', 1, 0))
    entries.append(get_symbol_prices("^NSEI", "NSE", 'US', 1, 0))
    entries.append(get_symbol_prices("^GSPC", "S&P 500", 'US', 1, 0))
    entries.append(get_symbol_prices("^DJI", "Dow Jones", 'US', 1, 0))
    entries.append(get_symbol_prices("^IXIC", "Nasdaq", 'US', 1, 0))
    entries.append(get_symbol_prices("^RUT", "Russel 2000", 'US', 1, 0))
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
        head=["Symbol", "Name", "Price", "Shlist Price", "Since Shlist", "Day Change", "Week Change", "Month Change", "Quarter Change", "Half Year", "Year Change"]
        entries.append(head)
        #for i in range(1,3):
        for i in range(1,sheet.nrows):
            entry = []
            sym  = str(sheet.cell_value(i, 1))
            if sym == '':
                continue
            name = str(sheet.cell_value(i, 0))
            print("Symbol: %r, Name: %r" %(sym, name))
            #print("\"%s\"" %(sheet.cell_value(i,4)))
            shortlist_price = float(sheet.cell_value(i, 4))

            entries.append(get_symbol_prices(sym, name, 'US', None, shortlist_price))
            #cur_price = internet.get_LTP('US', sym)
            #since_shortlist = cur_price / shortlist_price - 1  
            #day_change = internet.price_change('US', sym, name, 2, 'HOT')
            #week_change = internet.price_change('US', sym, name, 7, 'HOT')
            #month_change = internet.price_change('US', sym, name, 30, 'HOT')
            #quarter_change = internet.price_change('US', sym, name, 90, 'HOT')
            #halfyear_change = internet.price_change('US', sym, name, 180, 'HOT')
            #year_change = internet.price_change('US', sym, name, 365, 'HOT')
            #price = internet.get_LTP('US', sym)
            #entry.append(sym)
            #entry.append(name)
            #entry.append(str(price))
            #entry.append(str(shortlist_price))
            #entry.append(str(round(since_shortlist*100, 2))+'%')
            #entry.append(str(round(day_change*100, 2))+'%')
            #entry.append(str(round(week_change*100, 2))+'%')
            #entry.append(str(round(month_change*100, 2))+'%')
            #entry.append(str(round(quarter_change*100, 2))+'%')
            #entry.append(str(round(halfyear_change*100, 2))+'%')
            #entry.append(str(round(year_change*100, 2))+'%')
            #entries.append(entry)
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
    sheet.col(i).width = 20*367
    sheet.write(0, i, "Company", style_wrap)
    conf.COMP=i

    i+=1
    #Symbol
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Symbol", style_wrap)
    conf.SYM=i

    i+=1
    #Sector
    sheet.col(i).width = 10*367
    sheet.write(0, i, "Sector", style_wrap)
    conf.SEC=i

    i+=1
    #Sector
    sheet.col(i).width = 10*367
    sheet.write(0, i, "Industry", style_wrap)
    conf.IND=i

    i+=1
    #Since
    sheet.col(i).width = 10*367
    sheet.write(0, i, "Since", style_wrap)
    conf.SINCE=i

    i+=1
    #Current Price
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Current Price", style_wrap)
    conf.CUR_PR=i

    i+=1
    #Volume
    sheet.col(i).width = 7*367
    sheet.write(0, i, "Volume", style_wrap)
    conf.VOL=i

    i+=1
    #Beta
    sheet.col(i).width = 7*367
    sheet.write(0, i, "Beta", style_wrap)
    conf.BETA=i


    i+=1
    # Face Value
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Face Value", style_wrap)
    conf.FV=i

    i+=1
    # Market Cap in Cr
    sheet.col(i).width = 8*367
    sheet.write(0, i, "Market Cap", style_wrap)
    conf.MCAP=i

    i+=1
    # conf.FII
    sheet.col(i).width = 5*367
    sheet.write(0, i, "FII", style_wrap)
    conf.FII=i

    i+=1
    # conf.DII
    sheet.col(i).width = 5*367
    sheet.write(0, i, "DII", style_wrap)
    conf.DII=i

    i+=1
    # Promoter Stake
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Prom Stake", style_wrap)
    conf.PRM_S=i
    return i

def add_calc_header(sheet, i):
    #EPS
    sheet.col(i).width = 5*367
    sheet.write(0, i, "EPS", style_wrap)
    conf.EPS=i

    i+=1
    #DCF Price
    sheet.col(i).width = 5*367
    sheet.write(0, i, "DCF Price", style_wrap)
    conf.DCF_PR=i

    i+=1
    #MoS @50% Price
    sheet.col(i).width = 5*367
    #mos = "MoS Price @%r" %(stk['num']['margin_of_safety'])
    sheet.write(0, i, "MoS Price @50", style_wrap)
    conf.MOS_PR=i

    i+=1
    #Sale Price
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Sale Price", style_wrap)
    conf.SAL_PR=i

    i+=1
    #Return Rate @ Current Price
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Cur Price Ret Rate", style_wrap)
    conf.CUR_RT=i

    i+=1
    #Return Rate @ MoS Price
    sheet.col(i).width = 5*367
    sheet.write(0, i, "MoS Price Ret Rate", style_wrap)
    conf.MOS_RT=i
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
    # 2007 Index Percent Change
    sheet.col(i).width = 7*367
    sheet.write(0, i, "2007 Index Percent Change", style_wrap)
    conf.R2007_IPER_CHG=i

    i+=1
    # 2007 Percent Change
    sheet.col(i).width = 7*367
    sheet.write(0, i, "2007 Percent Change", style_wrap)
    conf.R2007_PER_CHG=i

    i+=1
    # 2007 Percent Change
    sheet.col(i).width = 9*367
    sheet.write(0, i, "Since Last Recession", style_wrap)
    conf.SINCE_LAST_PER_CHG=i

    i+=1
    # 2007 CAGR
    sheet.col(i).width = 5*367
    sheet.write(0, i, "2007 CAGR", style_wrap)
    conf.R2007_CAGR=i

    i+=1
    # 2007 Index CAGR
    sheet.col(i).width = 5*367
    sheet.write(0, i, "2007 Index CAGR", style_wrap)
    conf.R2007_ICAGR=i

    i+=1
    # Whole Beta
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Whole Beta", style_wrap)
    conf.W_BETA=i

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

    i+=1
    # TTM P/E
    sheet.col(i).width = 4*367
    sheet.write(0, i, "TTM P/E", style_wrap)
    conf.TTM_PE=i

    i+=1
    # DtoTE
    sheet.col(i).width = 5*367
    sheet.write(0, i, "DtoTE", style_wrap)
    conf.DTOTE=i

    #i+=1
    ## Interest Coverage
    #sheet.col(i).width = 4*367
    #sheet.write(0, i, "Intr Covr", style_wrap)
    #conf.INT_C=i

    i+=1
    # Profit Margin
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Profit Mgn", style_wrap)
    conf.PRF_M=i

    i+=1
    # RoE
    sheet.col(i).width = 4*367
    sheet.write(0, i, "RoE", style_wrap)
    conf.ROE=i

    i+=1
    # RoA
    sheet.col(i).width = 4*367
    sheet.write(0, i, "RoA", style_wrap)
    conf.ROA=i

    i+=1
    # RoCE
    sheet.col(i).width = 4*367
    sheet.write(0, i, "RoCE", style_wrap)
    conf.ROCE=i

    i+=1
    # Dividend Yield
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Div Yield", style_wrap)
    conf.DIV=i

    i+=1
    # Dividend Payout Ratio
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Div Payout", style_wrap)
    conf.DIV_PAY=i
    return i

def add_dcf_header(sheet, years):
    i=0
    i = add_basic_header(sheet, i)

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
    # Price Growth
    sheet.col(i).width = 5*367
    st = "%s yr Price Gr" %(years)
    sheet.write(0, i, st, style_wrap)
    conf.TEN_PRICE=i

    i+=1
    i = add_figs_growth_header(sheet, i, years)

    i+=1
    i = add_ratios_header(sheet, i)

    i+=1
    i = add_betas_header(sheet, i)

    i+=1
    # Float
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Float", style_wrap)
    conf.FLT=i
    print("Float: %d" %(conf.FLT))

    i+=1
    # Float Percent
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Float %", style_wrap)
    conf.FLT_PER=i

def add_price_change_header(sheet, i, sheet_type):
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Yr Price Change", style_wrap)
    conf.YR_PR_CHANGE=i
    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Qr Price Change", style_wrap)
    conf.QR_PR_CHANGE=i
    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Mon Price Change", style_wrap)
    conf.MON_PR_CHANGE=i
    i = i + 1
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Week Price Change", style_wrap)
    conf.WEEK_PR_CHANGE=i
    i = i + 1
    sheet.col(i).width = 8*367
    sheet.write(0, i, "Day Price Change", style_wrap)
    conf.DAY_PR_CHANGE=i
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


def write_to_price_change_excel(count, ash, stk, sheet_type):

    #DB.clear_dict(stk)

    if not isinstance(stk['num']['eps_20yr'], list):
        db=DB.open_db('Stocks')
        db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"num.eps_20yr":[]}})
        print("Setting eps_20yr to []")
        stk['num']['eps_20yr']=[]


#    if sheet_type == 'YEAR':
#        ash.write(count, conf.YR_PR_CHANGE, stk['price_change']['year'], style_percent)
#    if sheet_type == 'QUARTER':
#        ash.write(count, conf.QR_PR_CHANGE, stk['price_change']['quarter'], style_percent)
#    if sheet_type == 'MONTH':
#        ash.write(count, conf.MON_PR_CHANGE, stk['price_change']['month'], style_percent)
#    if sheet_type == 'WEEK':
#        ash.write(count, conf.WEEK_PR_CHANGE, stk['price_change']['week'], style_percent)
#    if sheet_type == 'DAY':
#        ash.write(count, conf.DAY_PR_CHANGE, stk['price_change']['day'], style_percent)

    ash.write(count, conf.YR_PR_CHANGE, stk['price_change']['year'], style_percent)
    ash.write(count, conf.QR_PR_CHANGE, stk['price_change']['quarter'], style_percent)
    ash.write(count, conf.MON_PR_CHANGE, stk['price_change']['month'], style_percent)
    ash.write(count, conf.WEEK_PR_CHANGE, stk['price_change']['week'], style_percent)
    ash.write(count, conf.DAY_PR_CHANGE, stk['price_change']['day'], style_percent)

    ash.write(count, conf.COMP, stk['bscs']['name'], style_text)
    ash.write(count, conf.PRM_S, stk['bscs']['promoter_stake']/100, style_percent)
    ash.write(count, conf.FII, stk['bscs']['fii_stake']/100, style_percent)
    ash.write(count, conf.DII, stk['bscs']['dii_stake']/100, style_percent)
    ash.write(count, conf.DIV, stk['Dividend']['yld']/100, style_percent)
    ash.write(count, conf.DIV_PAY, stk['Dividend']['payout_ratio']/100, style_percent)
    ash.write(count, conf.FLT, stk['bscs']['float']/100)
    try:
        ash.write(count, conf.FLT_PER, stk['bscs']['float_percent']/100, style_percent)
    except Exception:
        pass

    ash.write(count, conf.SYM, stk['bscs']['symbol'], style_text)
    ash.write(count, conf.SEC, stk['bscs']['sector'], style_text)
    ash.write(count, conf.IND, stk['bscs']['industry'], style_text)
    ash.write(count, conf.MCAP, stk['bscs']['mcap'], style_num)
    ash.write(count, conf.SINCE, stk['bscs']['since'], style_text)
    ash.write(count, conf.CUR_PR, stk['bscs']['price'])

    ash.write(count, conf.VOL, stk['bscs']['volume'])
    ash.write(count, conf.BETA, stk['bscs']['five_yr_beta'])

    ash.write(count, conf.FV, stk['bscs']['face_value'])

    try:
        pe  = round(stk['bscs']['price']/stk['fig']['ttm_eps'],2)
    except ZeroDivisionError:
        pe  = 0
    
    ash.write(count, conf.PE, pe)
    ash.write(count, conf.F_PE, stk['Ratios']['forward_PE'])
    ash.write(count, conf.TTM_PE, stk['Ratios']['ttm_PE'])

    ash.write(count, conf.YR_DAT, stk['num']['dcf_years'])
    ash.write(count, conf.PRICE_YR_DAT, stk['bscs']['price_years'])
    ash.write(count, conf.SAL_PR, round(sum(stk['num']['eps_20yr']),2), style_decimal)
    ash.write(count, conf.EPS, stk['fig']['ttm_eps'], style_decimal)
    ash.write(count, conf.DCF_PR, stk['num']['dcf_price']*2, style_decimal)
    ash.write(count, conf.MOS_PR, stk['num']['dcf_price'], style_decimal)
    ash.write(count, conf.CUR_RT, stk['num']['cp_return_rate'], style_percent)
    ash.write(count, conf.MOS_RT, stk['num']['dcf_return_rate'], style_percent)
    if len(stk['fig']['DtoE']) > 0:
        ash.write(count, conf.DTOTE, stk['fig']['DtoE'][-1])
    else:
        ash.write(count, conf.DTOTE, "-")
    # vpetla. Calcuate interest coverage ratio and uncomment this line
    ##ash.write(count, conf.INT_C, stk['fig']['INTR'][-1])
    if len(stk['fig']['ROE']) > 0:
        ash.write(count, conf.ROE, stk['fig']['ROE'][-1], style_percent)
    else:
        ash.write(count, conf.ROE, "-")
    if len(stk['fig']['ROA']) > 0:
        ash.write(count, conf.ROA, stk['fig']['ROA'][-1], style_percent)
    else:
        ash.write(count, conf.ROA, "-")
    # vpetla. Calcuate ROCE and uncomment this line
    ##ash.write(count, conf.ROCE, stk['fig']['ROCE'][-1])
    try:
        ash.write(count, conf.PRF_M, stk['fig']['PAT_M'][-1]/100, style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        ash.write(count, conf.TEN_PRICE, stk['fig']['price_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        ash.write(count, conf.TEN_SAL, stk['fig']['sales_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        ash.write(count, conf.TEN_PR, stk['fig']['profit_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        ash.write(count, conf.TEN_BK, stk['fig']['book_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))
    try:
        ash.write(count, conf.TEN_CSH, stk['fig']['cash_growth'], style_percent)
    except Exception as e:
        PRINT_ERR(str(e))

def check_and_write(ash, count, col, entry, index, factor, style):
    if len(entry) > 0:
        ash.write(count, col, entry[index]*factor, style)
    else:
        ash.write(count, col, 0, style)

#com : Company Work Book
#ash : All Stocks Work Sheet
#stk : Stock information
def write_to_excel(com, ash, stk, years):
    #wb = xlwt.Workbook()

    try:
        if not isinstance(stk['num']['eps_20yr'], list):
            db=DB.open_db('Stocks')
            db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"num.eps_20yr":[]}})
            print("Setting eps_20yr to []")
            stk['num']['eps_20yr']=[]
    except Exception as e:
        priint(str(e))

    #open a company sheet
    sheet = com.add_sheet(stk['bscs']['symbol'])
    sheet.col(0).width = 28*367
    sheet.col(1).width = 10*367
    sheet.col(3).width = 10*367

    if not stk['bscs']['dii_stake']:
        stk['bscs']['dii_stake']=0
    if not 'yld' in stk['Dividend']:
        db=DB.open_db('Stocks')
        db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"Dividend.yld":0}})
        db.US_Stocks.update({"bscs.symbol":stk['bscs']['symbol']},{'$set':{"Dividend.payout_ratio":0}})
        stk['Dividend']['yld']=0
        stk['Dividend']['payout_ratio']=0
    if not 'interest_coverage' in stk['Ratios']:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.interest_coverage", 0)
        stk['Ratios']['interest_coverage']=0
    if not 'forward_PE' in stk['Ratios']:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.forward_PE", 0)
        stk['Ratios']['forward_PE']=0
    if not 'ttm_PE' in stk['Ratios']:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.ttm_PE", 0)
        stk['Ratios']['ttm_PE']=0
    if not 'float' in stk['bscs']:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "bscs.float", 0)
        stk['bscs']['float'] = 0
    if not 'float_percent' in stk['bscs'] or not stk['bscs']['float_percent']:
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
    sheet.write(i, 1, stk['bscs']['name'])
    ash.write(conf.COUNT, conf.COMP, stk['bscs']['name'], style_text)

    sheet.write(i, 3, "Promoter Stake")
    sheet.write(i, 4, stk['bscs']['promoter_stake']/100, style_percent)
    ash.write(conf.COUNT, conf.PRM_S, stk['bscs']['promoter_stake']/100, style_percent)
    ash.write(conf.COUNT, conf.FII, stk['bscs']['fii_stake']/100, style_percent)
    ash.write(conf.COUNT, conf.DII, stk['bscs']['dii_stake']/100, style_percent)
    ash.write(conf.COUNT, conf.DIV, stk['Dividend']['yld']/100, style_percent)
    ash.write(conf.COUNT, conf.DIV_PAY, stk['Dividend']['payout_ratio']/100, style_percent)
   
    #Betas
    if stk['fig']['betas']:
        if stk['fig']['betas']['recession']['2007']:
            ash.write(conf.COUNT, conf.R2007_BETA, round(stk['fig']['betas']['recession']['2007']['beta'], 2), style_decimal)
            ash.write(conf.COUNT, conf.R2007_ALPHA, round(stk['fig']['betas']['recession']['2007']['alpha'], 2), style_decimal)
            ash.write(conf.COUNT, conf.R2007_PURE_ALPHA, round(stk['fig']['betas']['recession']['2007']['alpha_pure'], 2), style_decimal)
            try:
                ash.write(conf.COUNT, conf.R2007_IPER_CHG, round(stk['fig']['betas']['recession']['2007']['Index Percent Change'], 2), style_percent)
                ash.write(conf.COUNT, conf.R2007_PER_CHG, round(stk['fig']['betas']['recession']['2007']['Percent Change'], 2), style_percent)
                ash.write(conf.COUNT, conf.SINCE_LAST_PER_CHG, round(stk['fig']['betas']['since_last_recession']['Percent Change'], 2), style_decimal)
            except Exception:
                pass
            ash.write(conf.COUNT, conf.R2007_CAGR, round(stk['fig']['betas']['recession']['2007']['CAGR'], 2), style_decimal)
            ash.write(conf.COUNT, conf.R2007_ICAGR, round(stk['fig']['betas']['recession']['2007']['Index_CAGR'], 2), style_decimal)
        if stk['fig']['betas']['whole']:
            ash.write(conf.COUNT, conf.W_BETA, round(stk['fig']['betas']['whole']['beta'], 2), style_decimal)
            ash.write(conf.COUNT, conf.W_ALPHA, round(stk['fig']['betas']['whole']['alpha'], 2), style_decimal)
            ash.write(conf.COUNT, conf.W_PURE_ALPHA, round(stk['fig']['betas']['whole']['alpha_pure'], 2), style_decimal)

    ash.write(conf.COUNT, conf.FLT, stk['bscs']['float']/100)
    ash.write(conf.COUNT, conf.FLT_PER, stk['bscs']['float_percent']/100, style_percent)

    i += 1 #row 5
    sheet.write(i, 0, "Symbol")
    sheet.write(i, 1, stk['bscs']['symbol'])
    ash.write(conf.COUNT, conf.SYM, stk['bscs']['symbol'], style_text)
    ash.write(conf.COUNT, conf.SEC, stk['bscs']['sector'], style_text)
    ash.write(conf.COUNT, conf.IND, stk['bscs']['industry'], style_text)
    ash.write(conf.COUNT, conf.SINCE, stk['bscs']['since'], style_text)

    sheet.write(i, 3, "Public Stake")
    sheet.write(i, 4, stk['bscs']['pub_stake']/100, style_percent)

    i += 1 #row 6
    sheet.write(i, 0, "Price")
    sheet.write(i, 1, stk['bscs']['price'])
    ash.write(conf.COUNT, conf.CUR_PR, stk['bscs']['price'])

    sheet.write(i, 3, "Volume")
    sheet.write(i, 4, stk['bscs']['volume'])
    ash.write(conf.COUNT, conf.VOL, stk['bscs']['volume'])

    i += 1 #row 7
    sheet.write(i, 0, "Face Value")
    sheet.write(i, 1, stk['bscs']['face_value'])
    ash.write(conf.COUNT, conf.FV, stk['bscs']['face_value'])

    i += 1 #row 8
    sheet.write(i, 0, "P/E")
    try:
        pe  = round(stk['bscs']['price']/stk['fig']['ttm_eps'],2)
    except ZeroDivisionError:
        pe  = 0
    sheet.write(i, 1, pe)
    ash.write(conf.COUNT, conf.PE, pe)
    try:
        ash.write(conf.COUNT, conf.F_PE, stk['Ratios']['forward_PE'])
    except AttributeError:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.forward_PE", 0)
    try:
        ash.write(conf.COUNT, conf.TTM_PE, stk['Ratios']['ttm_PE'])
    except AttributeError:
        db=DB.open_db('Stocks')
        DB.update_field(db.US_Stocks, stk['bscs']['symbol'], "Ratios.ttm_PE", 0)

    i += 1
    sheet.write(i, 0, "Five Year Beta")
    sheet.write(i, 1, stk['bscs']['five_yr_beta'])
    ash.write(conf.COUNT, conf.BETA, stk['bscs']['five_yr_beta'])

    i = 10 #row 11
    sheet.write(i, 0, "Growth Rate(1-5 Years)")
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
    #ash.write(conf.COUNT, conf.YR_DAT, len(stk['fig']['Sales']))
    sheet.write(i, 4, years)
    sheet.write(i, 5, years)
    sheet.write(i, 6, years)
    sheet.write(i, 7, years)
    ash.write(conf.COUNT, conf.YR_DAT, years)
    ash.write(conf.COUNT, conf.PRICE_YR_DAT, stk['bscs']['price_years'])

    i += 1 #row 13
    sheet.write(i, 0, "Growth Rate(9-10 Years)")
    sheet.write(i, 1, Formula("B12 * 0.8"), style_percent)
    sheet.write(i, 3, "Growth Rate", style_bold)
    sheet.write(i, 4, stk['fig']['book_growth'], style_percent)
    sheet.write(i, 5, stk['fig']['sales_growth'], style_percent)
    sheet.write(i, 6, stk['fig']['cash_growth'], style_percent)
    sheet.write(i, 7, stk['fig']['profit_growth'], style_percent)

    i += 1 #row 14
    sheet.write(i, 0, "Terminal Growth Rate(10-15 Years)")
    sheet.write(i, 1, Formula("B13 * 0.5"), style_percent)

    i += 1 #row 15
    sheet.write(i, 0, "Terminal Growth Rate(16-20 Years)")
    sheet.write(i, 1, Formula("B14 * 0.8"), style_percent)

    i += 1 #row 16
    sheet.write(i, 0, "Discount Rate")
    sheet.write(i, 1, stk['num']['discount_rate'], style_percent)

    i += 1 #row 17
    sheet.write(i, 0, "Inflation")
    sheet.write(i, 1, stk['num']['inflation'], style_percent)

    i += 1 #row 18
    sheet.write(i, 0, "Margin of Safety")
    sheet.write(i, 1, stk['num']['margin_of_safety'], style_percent)

    # Earning Calculation
    i = 21 #row 22
    sheet.write(i, 0, "Year")
    now = datetime.datetime.now()
    now = int(now.year) - 1 # Year 2018
    sheet.write(i, 1, now)

    i += 1 #row 23
    sheet.write(i, 0, "EPS")
    sheet.write(i, 1, stk['fig']['ttm_eps'])

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

    i += 1 #row 35
    yr = "EPS by %r at %r percent inflation" % (now + 5, (stk['num']['inflation'])*100)
    sheet.write(i, 0, yr)
    sheet.write(i, 1, Formula("$B$31 * ((1-$B$17)^5)"), style_decimal)

    i += 2 #row 36
    sheet.write(i, 0, "Earnings after 20 years")
    sheet.write(i, 1, Formula("SUM($B$25:$K$25) + SUM($B$28:$K$28)"), style_decimal)
    ash.write(conf.COUNT, conf.SAL_PR, round(sum(stk['num']['eps_20yr']),2), style_decimal)

    i += 1 #row 37
    sheet.write(i, 0, "Today's Value with Inflation")
    sheet.write(i, 1, Formula("($B$35 * ((1-$B$17)^20)) * $B$9"), style_decimal)
    ash.write(conf.COUNT, conf.DCF_PR, stk['num']['dcf_price']*2, style_decimal)
    ash.write(conf.COUNT, conf.EPS, stk['fig']['ttm_eps'], style_decimal)

    i += 1 #row 38
    sheet.write(i, 0, "Price with Margin of Safety")
    sheet.write(i, 1, Formula("$B$36*$B$18"), style_decimal)
    ash.write(conf.COUNT, conf.MOS_PR, stk['num']['dcf_price'], style_decimal)

    i += 1  # row 39
    sheet.write(i, 0, "Current Price", style_bold)
    sheet.write(i, 1, stk['bscs']['price'], style_bold)
    sheet.write(i, 2, "Profit", style_bold)

    i += 1 #row 40
    sheet.write(i, 0, "Value of MoS Price after 20 years with inflation")
    sheet.write(i, 1, Formula("$B$37*((1+$B$17)^20)"), style_decimal)
    sheet.write(i, 2, Formula("$B$35-$B$38"), style_decimal)

    i += 1 #row 4
    sheet.write(i, 0, "Rate of return at Current Price")
    sheet.write(i, 1, Formula("($B$35/$B$38)^0.05-1"), style_percent)
    ash.write(conf.COUNT, conf.CUR_RT, stk['num']['cp_return_rate'], style_percent)
    #sheet.write(i, 1, Formula("((($B$35/$B$39)^(1/$K$27-$B$22))-1)))"), style_percent)

    i += 1 #row 41
    sheet.write(i, 0, "Rate of return at MoS Price")
    sheet.write(i, 1, Formula("($B$35/$B$37)^0.05-1"), style_percent)
    ash.write(conf.COUNT, conf.MOS_RT, stk['num']['dcf_return_rate'], style_percent)
   
    #Ratios
    check_and_write(ash, conf.COUNT, conf.DTOTE, stk['fig']['DtoE'], -1, 1, style_num)
    # vpetla. Calcuate interest coverage ratio and uncomment this line
    ##ash.write(conf.COUNT, conf.INT_C, stk['fig']['INTR'][-1])
    check_and_write(ash, conf.COUNT, conf.ROE, stk['fig']['ROE'], -1, 1, style_percent)
    check_and_write(ash, conf.COUNT, conf.ROA, stk['fig']['ROA'], -1, 1, style_percent)
    # vpetla. Calcuate ROCE and uncomment this line
    ##ash.write(conf.COUNT, conf.ROCE, stk['fig']['ROCE'][-1])
    check_and_write(ash, conf.COUNT, conf.PRF_M, stk['fig']['PAT_M'], -1, 1/100, style_percent)
    ash.write(conf.COUNT, conf.MCAP, stk['bscs']['mcap'], style_num)
    ash.write(conf.COUNT, conf.YR_PR_CHANGE, stk['price_change']['year'], style_percent)
    ash.write(conf.COUNT, conf.QR_PR_CHANGE, stk['price_change']['quarter'], style_percent)
    ash.write(conf.COUNT, conf.MON_PR_CHANGE, stk['price_change']['month'], style_percent)
    ash.write(conf.COUNT, conf.WEEK_PR_CHANGE, stk['price_change']['week'], style_percent)
    ash.write(conf.COUNT, conf.DAY_PR_CHANGE, stk['price_change']['day'], style_percent)
    ash.write(conf.COUNT, conf.TEN_PRICE, stk['fig']['price_growth'], style_percent)
    ash.write(conf.COUNT, conf.TEN_SAL, stk['fig']['sales_growth'], style_percent)
    ash.write(conf.COUNT, conf.TEN_PR, stk['fig']['profit_growth'], style_percent)
    ash.write(conf.COUNT, conf.TEN_BK, stk['fig']['book_growth'], style_percent)
    ash.write(conf.COUNT, conf.TEN_CSH, stk['fig']['cash_growth'], style_percent)
    #sheet.write(i, 1, Formula("((($B$35/$B$37)^(1/$K$27-$B$22))-1)))"), style_percent)

#    excel = "excel_files/%s.xls" %(stk['bscs']['name'])

#    PRINT("Writing to %s"%(excel))
#    wb.save(excel)


