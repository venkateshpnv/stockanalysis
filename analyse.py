import time

#Web Driver
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Parsing HTML
import requests 
from bs4 import BeautifulSoup 

# Excel operations
import csv
import xlrd
import xlwt
from xlwt import Workbook, Formula

# Date
import datetime
from datetime import date
import arrow

#Regular Expressions
import re

#List Files
#import os
import glob

import math

MAX_YEARS = 20
#Sales, PAT, Cash Flow, Book Value
GROWTH_PARAMS = 4

# Number of figures we are tracking data for.
indices=0
YEARS = indices
indices+=1
SALES = indices
indices+=1
#Profit Before Taxes
PBT = indices
indices+=1
TAX = indices
indices+=1
#Profit After Taxes
PAT = indices
indices+=1
#Unadjusted EPS
EPS = indices
indices+=1
CASH = indices
indices+=1
BOOK = indices
indices+=1
DtoE = indices
indices+=1

# Percentage change in growth over a period of time
gr1to5_percent   = 1
gr6to8_percent   = 0.7
gr9to10_percent  = 0.8
gr11to15_percent = 0.5
gr16to20_percent = 0.8

class Basics:
    def __init__(self):
        self.name   = 'DEADCOW'
        self.symbol = 'DEAD'
        self.price  = 0
        self.promoter_stake = 0
        self.corp_stake     = 0
        self.pub_stake      = 0
        self.fii_stake      = 0
        self.dii_stake      = 0
        self.others_stake   = 0
        self.face_value     = 0
        self.volume         = 0

class Ratios:
    def __init(self):
        self.book_value = 0
        # Percentages
        self.ROA = 0
        self.ROE = 0
        self.ROCE = 0

        # Debt/Equity
        self.DtoE = 0
        
        # Interest Coverage
        self.IC = 0

class Figures:
    # row 0 - year
    # row 1 - sales
    # row 2 - profit
    # row 3 - free cash flow
    # row 4 - book value
    # 20 years of data of sales, profit etc
    #entries = [[0] * MAX_YEARS for i in range(indices)]
    entries = []
    # number of years of data we have for each field.
    # ex: 10 years of book value, 8 years of cash flow etc.
    #fig_years = [0] * (indices)
    #fig_years = []

    def __init(self):
        self.ttm_eps = 0
        # Long Term Debt
        self.lt_debt = 0
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0
        self.growth = 0
        #self.entries = [[0] * MAX_YEARS for i in range(indices)]
        #self.entries = [[0 for i in range(MAX_YEARS)] for j in range(indices)]
        self.entries = [0 for i in range(indices)]
        #self.fig_years = [indices]
        #self.fig_years = [0 for i in range(indices)]

class Numbers:
    # figures in percentages
    discount_rate = 0
    inflation     = 0
    growth_1to5   = 0
    growth_6to8   = 0
    growth_9to10  = 0
    growth_11to15 = 0
    growth_16to20 = 0

    # current eps
    eps = 0
    # Total earnings for 20 yrs
    eps_20yr = []

    # start and end years
    fig_yr  = 2018
    cur_yr  = 2019
    term_yr = 2029

    # DCF price and return rate
    dcf_price = 0
    # Inflated EPS Price
    inflated_eps_price = 0
    margin_of_safety = 0
    # return rate at DCF price
    dcf_return_rate  = 0
    # return rate at current price
    cp_return_rate   = 0

class Stock:
    def __init__(self):
        self.name = "Hello"
        self.bscs = Basics()
        self.fig  = Figures()
        self.num  = Numbers()

#Supportive calls
def PRINT_DBG(x):
    None
    #print(x)
def PRINT(x):
    print(x)

def goto(linenum):
    global line
    line=linenum

def p2f(x):
    try:
        val = float(x.strip('%'))
    except ValueError:
        return 0
    return val

def str_to_int(x):
    try:
        val = int(x)
    except ValueError:
        return 0
    return val

def str_to_float(x):
    try:
        val = float(x)
    except ValueError:
        return 0
    return val

def str_to_float_valid(x):
    try:
        val = float(x)
        return True
    except ValueError:
        return False

def write_to_excel(stk):
    wb = xlwt.Workbook()
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

    sheet = wb.add_sheet(stk.bscs.symbol)

    i = 0
    sheet.write(i, 0, "Date", style_bold)
    sheet.write(i, 1, arrow.now().format('DD-MM-YYYY'))
    #sheet.write(0, 1, str(date.today()))

    i = 2
    sheet.write(i, 0, "Basics")

    i += 1 #row 4
    sheet.write(i, 0, "Name")
    sheet.write(i, 1, stk.bscs.name)
    sheet.write(i, 3, "Promoter Stake")
    sheet.write(i, 4, stk.bscs.promoter_stake)

    i += 1 #row 5
    sheet.write(i, 0, "Symbol")
    sheet.write(i, 1, stk.bscs.symbol)
    sheet.write(i, 3, "Public Stake")
    sheet.write(i, 4, stk.bscs.pub_stake)

    i += 1 #row 6
    sheet.write(i, 0, "Price")
    sheet.write(i, 1, stk.bscs.price)

    i += 1 #row 7
    sheet.write(i, 0, "Face Value")
    sheet.write(i, 1, stk.bscs.face_value)

    i += 1 #row 8
    sheet.write(i, 0, "P/E")
    sheet.write(i, 1, round(stk.bscs.price/stk.fig.ttm_eps,2))


    i = 10 #row 11
    sheet.write(i, 0, "Growth Rate(1-5 Years)")
    sheet.write(i, 1, stk.num.growth_1to5, style_percent)

    sheet.write(i, 4, "Book Value", style_bold)
    sheet.write(i, 5, "Sales", style_bold)
    sheet.write(i, 6, "Cash Flow", style_bold)
    sheet.write(i, 7, "PAT", style_bold)


    i += 1 #row 12
    sheet.write(i, 0, "Growth Rate(6-8 Years)")
    # TODO replace 0.7, 0.8 with variables.
    sheet.write(i, 1, Formula("B11 * 0.7"), style_percent)

    sheet.write(i, 3, "Years", style_bold)
    sheet.write(i, 4, len(stk.fig.entries[BOOK]))
    sheet.write(i, 5, len(stk.fig.entries[SALES]))
    sheet.write(i, 6, len(stk.fig.entries[CASH]))
    sheet.write(i, 7, len(stk.fig.entries[PAT]))

    i += 1 #row 13
    sheet.write(i, 0, "Growth Rate(9-10 Years)")
    sheet.write(i, 1, Formula("B12 * 0.8"), style_percent)
    sheet.write(i, 3, "Growth Rate", style_bold)
    sheet.write(i, 4, stk.fig.book_growth, style_percent)
    sheet.write(i, 5, stk.fig.sales_growth, style_percent)
    sheet.write(i, 6, stk.fig.cash_growth, style_percent)
    sheet.write(i, 7, stk.fig.profit_growth, style_percent)

    i += 1 #row 14
    sheet.write(i, 0, "Terminal Growth Rate(10-15 Years)")
    sheet.write(i, 1, Formula("B13 * 0.5"), style_percent)

    i += 1 #row 15
    sheet.write(i, 0, "Terminal Growth Rate(16-20 Years)")
    sheet.write(i, 1, Formula("B14 * 0.8"), style_percent)

    i += 1 #row 16
    sheet.write(i, 0, "Discount Rate")
    sheet.write(i, 1, stk.num.discount_rate, style_percent)

    i += 1 #row 17
    sheet.write(i, 0, "Inflation")
    sheet.write(i, 1, stk.num.inflation, style_percent)

    i += 1 #row 18
    sheet.write(i, 0, "Margin of Safety")
    sheet.write(i, 1, stk.num.margin_of_safety, style_percent)

    # Earning Calculation
    i = 21 #row 22
    sheet.write(i, 0, "Year")
    now = datetime.datetime.now()
    now = int(now.year) - 1 # Year 2018
    sheet.write(i, 1, now)

    i += 1 #row 23
    sheet.write(i, 0, "EPS")
    sheet.write(i, 1, stk.fig.ttm_eps)

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


    i = 26 #row 27
    sheet.write(i, 0, "Terminal Value")
    for j in range(11,21):
        sheet.write(i, j-10, now+j, style_bold)

    i += 1 #row 28
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

    i += 2 #row 30
    sheet.write(i, 0, "EPS by Year")

    # Earnings by 2024
    i += 1 #row 31
    now += 1 #2024
    yr = "%r" %(now + 5)
    sheet.write(i, 0, yr)
    sheet.write(i, 1, Formula("SUM($B$25:$F$25)"), style_decimal)

    # Earnings by 2029
    i += 1 #row 32
    yr = "%r" % (now + 10)
    sheet.write(i, 0, yr)
    sheet.write(i, 1, Formula("SUM($B$25:$K$25)"), style_decimal)

    i += 1 #row 33
    yr = "EPS by %r at %r percent inflation" % (now + 5, (stk.num.inflation)*100)
    sheet.write(i, 0, yr)
    sheet.write(i, 1, Formula("$B$31 * ((1-$B$17)^5)"), style_decimal)

    i += 2 #row 35
    sheet.write(i, 0, "Earnings after 20 years")
    sheet.write(i, 1, Formula("SUM($B$25:$K$25) + SUM($B$28:$K$28)"), style_decimal)

    i += 1 #row 36
    sheet.write(i, 0, "Today's Value with Inflation")
    sheet.write(i, 1, Formula("$B$35 * ((1-$B$17)^20)"), style_decimal)

    i += 1 #row 37
    sheet.write(i, 0, "Price with Margin of Safety")
    sheet.write(i, 1, Formula("$B$36*$B$18"), style_decimal)

    i += 1  # row 38
    sheet.write(i, 0, "Current Price", style_bold)
    sheet.write(i, 1, stk.bscs.price, style_bold)
    sheet.write(i, 2, "Profit", style_bold)

    i += 1 #row 39
    sheet.write(i, 0, "Value of MoS Price after 20 years with inflation")
    sheet.write(i, 1, Formula("$B$37*((1+$B$17)^20)"), style_decimal)
    sheet.write(i, 2, Formula("$B$35-$B$38"), style_decimal)

    i += 1 #row 40
    sheet.write(i, 0, "Rate of return at Current Price")
    sheet.write(i, 1, Formula("($B$35/$B$38)^0.05-1"), style_percent)
    #sheet.write(i, 1, Formula("((($B$35/$B$39)^(1/$K$27-$B$22))-1)))"), style_percent)

    i += 1 #row 41
    sheet.write(i, 0, "Rate of return at MoS Price")
    sheet.write(i, 1, Formula("($B$35/$B$37)^0.05-1"), style_percent)
    #sheet.write(i, 1, Formula("((($B$35/$B$37)^(1/$K$27-$B$22))-1)))"), style_percent)

    excel = "excel_files/%s.xls" %(stk.bscs.name)

    PRINT("Writing to %s"%(excel))
    wb.save(excel)

def get_stock_page(stock):
    driver = webdriver.Firefox()
    #driver.get("http://www.google.com")
    #elem = driver.find_element_by_name("q")
    driver.get("http://www.ratestar.in/home")
    old_url = driver.current_url
    elem = driver.find_element_by_name("txtStock")
    #driver.get("http://www.python.org")
    #assert "Python" in driver.title
    #elem = driver.find_element_by_name("q")
    
    #stock='LT Foods Ltd.'
    elem.clear()
    for i in range(len(stock)):
        elem.send_keys(str(stock[i]))
        time.sleep(100.0/1000.0)
    #elem.send_keys(stock, Keys.ARROW_DOWN)
    time.sleep(2)
    elem.send_keys(Keys.RETURN)
    
    time.sleep(20)
    html_src=driver.page_source
    #PRINT_DBG(str(html_src))

    if driver.current_url == old_url:
        PRINT_DBG("Unable to parse %r" %(stock))
        f = open("unparsed_stocks.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        #PRINT_DBG("Found stock %r" %(stock))
        html_file = "html_pages/%s.html" %(stock)  
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

def get_all_stocks_html():
    wb = xlrd.open_workbook("BSE_Stocks.xls")
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
    for i in range(3986,sheet.nrows):
    #for i in range(1,10):
        PRINT("%r: %r" %(i, sheet.cell_value(i, 2)))
        get_stock_page(sheet.cell_value(i,2))
        
#    f = open('NSE_Stocks.csv')
#    #f = open('BSE_Stocks.csv')
#    csv_f = csv.reader(f)
#    for row in csv_f:
#        PRINT_DBG(row)
#        #PRINT_DBG(row[1])
#        #PRINT_DBG(row[0], row[1], row[2],)

def calculate_PAT(stk):
    entry=[]
    for i in range(len(stk.fig.entries[PBT])):
        entry.append(round(stk.fig.entries[PBT][i] - stk.fig.entries[TAX][i],2))
    stk.fig.entries.insert(PBT, entry)
    PRINT_DBG("PAT:")
    PRINT_DBG(stk.fig.entries[PBT])

def populate(stk, div, row, convert):
    entry = []
    #f = open("figs.html", "w")
    #st = "############################## Row %r #######################" %(row)
    #f.write(st)
    #f.write(str(div.prettify()))
    #f.close()

    i = 0
    div2 = div.find_next("div")
    #PRINT_DBG(div2)

    while True:
        c = str(div2['class'])
        # If end of class? stop
        if c == "['clear']":
            #PRINT_DBG("Found Clear Class")
            break
        # If html page does not display? skip
        if div2.has_attr("style"):
            #PRINT_DBG("Has attr style")
            style = str(div2['style'])
            #PRINT_DBG("Style : %r " %(style))
            if style == 'display: none;':
                PRINT_DBG("Skipping: %r" %(div2))
                div2 = div2.find_next("div")
                PRINT_DBG("Next: %r" %(div2))
                continue

        val = div2.get_text().lstrip().rstrip().replace(",","")
        #If the value is valid? append else skip
        if convert == 1 and str_to_float_valid(val):
            entry.append(str_to_float(val))
        else:
            entry.append(val)
        div2 = div2.find_next("div")
        i += 1

    #div_tags = div.find_all("div")
    #for tag in div_tags:
    #    entry.append(tag.get_text().lstrip().rstrip().replace(",", ""))
    #    i += 1

    entry.reverse()
    if convert:
        entry = list(map(float, entry))
    #stk.fig.entries.append(entry)
    stk.fig.entries.insert(row, entry)
    #PRINT_DBG("Entries:")
    #PRINT_DBG(stk.fig.entries[row])

    #stk.fig.fig_years.append(i)
    #stk.fig.fig_years.insert(row, i)
    #PRINT_DBG("Years : %r" % (stk.fig.fig_years[row]))

def populate_item(stk, pattern, section, row, convert):
    div = section.find("div", text=pattern)
    if not div:
        print("No Match")
        return False
    div = div.parent
    div = div.find_next("div", {"class": "CHead"})
    populate(stk, div, row, convert)
    return True

def populate_stock(html_page):
    stk = Stock()
    # we need a parser,Python built-in HTML parser is enough . 
    soup=BeautifulSoup(html_page,'html.parser')      
    # l is the list which contains all the text i.e news 

############# BASICS ##################
    #Company Name
    try:
        l=soup.find(id='lblCompany').get_text()
    except:
        return None
    stk.bscs.name = l

    # Ticker
    l=soup.find(id='lblNSE').get_text()
    l = l.split(": ", 1)[1]
    stk.bscs.symbol = l

    # Price
    l=soup.find(id='lblLTP').get_text()
    try:
        stk.bscs.price = str_to_float(l)
    except ValueError:
        stk.bscs.price = 0
    if stk.bscs.price < 1:
        return None

    # Face Value
    l=soup.find(id='lblFaceValue').get_text()
    try:
        stk.bscs.face_value = int(l)
    except ValueError:
        stk.bscs.face_value = 10

    # Volume
    l=soup.find(id='lblVolume').get_text()
    try:
        stk.bscs.volume = int(l)
    except ValueError:
        stk.bscs.volume = 0

    if stk.bscs.volume < 50000:
        return None

    PRINT_DBG("Volume %r" %(stk.bscs.volume))

    #soup=BeautifulSoup(html_page,'lxml')     
    # Promoter Stake
    divTag = soup.find("div", {"class": "com-mid-share-wrap", "align": "right"})
    divTag2 = divTag
    for i in range(7):
        divTag2 = divTag2.find_next("div")
    #divTag2 = divTag.find("div", {"class" : "float-lt com-mid-share-tab2", "align" : "right"})
    li = divTag2.ul.li
    pshare = li.get_text()
    stk.bscs.promoter_stake = p2f(pshare.lstrip())
    li = li.find_next("li")
    # Corporate Stake
    pshare = li.get_text()
    stk.bscs.corp_stake = p2f(pshare.lstrip())
    li = li.find_next("li")
    # Public Stake
    pshare = li.get_text()
    stk.bscs.pub_stake = p2f(pshare.lstrip())

    divTag = divTag.find_next("div", {"class": "com-mid-share-table-wrap", "align": "right"})
    divTag2 = divTag
    for i in range(3):
        divTag2 = divTag2.find_next("div")

    li = divTag2.ul.li
    # FII Stake
    #pshare = divTag2.ul.li.get_text()
    pshare = li.get_text()
    stk.bscs.fii_stake = p2f(pshare.lstrip())
    li = li.find_next("li")
    # DII Stake
    #pshare = divTag2.ul.li.find_next_sibling("li").get_text()
    pshare = li.get_text()
    stk.bscs.dii_stake = p2f(pshare.lstrip())
    li = li.find_next("li")
    #Others Stake
    #pshare = divTag2.ul.li.find_next_sibling("li").find_next_sibling("li").get_text()
    pshare = li.get_text()
    stk.bscs.others_stake = p2f(pshare.lstrip())



############# BASICS ##################


############# FIGURES ##################
    #Get Annual Results.
    #Prefer consolidated.

    annual = soup.find("section", {"id":"Annual"})

    annual_cons = annual.find("table", {"id": "tblAnnualCons", "class": "table table-bordered table-striped"})
    if annual_cons:
        if annual_cons.has_attr("style") and str(annual_cons['style']) == 'display: none;':
            annual_cons = annual.find("table", {"id": "tblAnnualStd", "class": "table table-bordered table-striped"})
            if not annual_cons:
                PRINT_DBG("No Standalone results. Checking Annual")
                annual_cons = annual.find("table", {"id": "tblAnnual", "class": "table table-bordered table-striped"})
                if not annual_cons:
                    assert "No Annual Results found"
    else:
        PRINT_DBG("No Consolidated results. Checking for standalone results")
        annual_cons = annual.find("table", {"id": "tblAnnualStd", "class": "table table-bordered table-striped"})
        if not annual_cons:
            PRINT_DBG("No Standalone results. Checking Annual")
            annual_cons = annual.find("table", {"id": "tblAnnual", "class": "table table-bordered table-striped"})
            if not annual_cons:
                assert "No Annual Results found"

    PRINT_DBG(annual_cons)
    #Years
    PRINT_DBG("YEARS: %r" %(YEARS))
    pattern = re.compile(r'Description\n')
    populate_item(stk, pattern, annual_cons, YEARS, 0)
    PRINT_DBG(stk.fig.entries[YEARS])
    #Sales
    PRINT("SALES: %r"%(SALES))
    pattern = re.compile(r'Net Sales')
    if populate_item(stk, pattern, annual_cons, SALES, 1) is False:
        pattern = re.compile(r'Net Interest Income')
        div = annual_cons.find(text=pattern)
        PRINT_DBG(div.parent.parent)
        if div is None:
            return None
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, SALES, 1)
        #populate_item(stk, pattern, annual_cons, SALES, 1)
    PRINT_DBG(stk.fig.entries[SALES])
    #Profit Before Taxes
    PRINT_DBG("PBT: %r" %(PBT))
    pattern = re.compile(r'PBT\n')
    populate_item(stk, pattern, annual_cons, PBT, 1)
    PRINT_DBG(stk.fig.entries[PBT])
    #Tax
    PRINT_DBG("TAX: %r" %(TAX))
    pattern = re.compile(r'Tax\n')
    populate_item(stk, pattern, annual_cons, TAX, 1)
    PRINT_DBG(stk.fig.entries[TAX])

    PRINT_DBG("PAT: %r" %(PAT))
    calculate_PAT(stk)

    #EPS
    PRINT_DBG("EPS: %r, indices: %r" %(EPS, indices))
    pattern = re.compile(r'Unadjusted EPS\n')
    populate_item(stk, pattern, annual_cons, EPS, 1)
    PRINT_DBG(stk.fig.entries[EPS])

    stk.fig.ttm_eps = stk.fig.entries[EPS][-1]
    PRINT("TTM EPS: %r" %(stk.fig.ttm_eps))
    if stk.fig.ttm_eps <= 0:
        PRINT("Negative EPS")
        return None

    # Retrieve Operating Cash Flow
    PRINT_DBG("Cash Flow")
    cash = soup.find("section", {"id":"Cash"})
    cash_flow = cash.find("table", {"id": "tbl_CashFlowCons"})
    if cash_flow:
        if cash_flow.has_attr("style") and str(cash_flow['style']) == 'display: none;':
            cash_flow = cash.find("table", {"id": "tbl_CashFlowStd"})
            if not cash_flow:
                cash_flow = cash.find("table", {"id": "Cash"})
                if not cash_flow:
                    assert "No Cash Flow numbers"
    else:
        cash_flow = cash.find("table", {"id": "tbl_CashFlowStd"})
        if not cash_flow:
            cash_flow = cash.find("table", {"id": "Cash"})
            if not cash_flow:
                assert "No Cash Flow numbers"

    pattern = re.compile(r'Cash From Operating Activity')
    div = cash_flow.find(text=pattern)
    div = div.parent.parent
    div = div.find_next("div", {"class": "CHead"})
    populate(stk, div, CASH, 1)
    PRINT_DBG(stk.fig.entries[CASH])

    fin_ratios = soup.find("section", {"id": "Financial"})
    #f = open("man_fin_ratios.html", "w")
    #f.write(fin_ratios.prettify())
    #f.close()
    fin = fin_ratios.find("div", {"id": "DivFinancialRatios_Cons"})
    if fin:
        if fin.has_attr("style") and str(fin['style']) == 'display: none;':
            print("Fin Ratios Display None")
            fin = fin_ratios.find("div", {"id": "DivFinancialRatios_Std"})
            if not fin:
                assert "No Fin Ratios Found"
    else:
        fin = fin_ratios.find("div", {"id": "DivFinancialRatios_Std"})
        if not fin:
            assert "No Fin Ratios Found"

#label: BOOK
    # Retrieve Book Value
    PRINT_DBG("Book Value")
    pattern = re.compile(r'Book Value')
    div = fin.find(text=pattern)
    if not div:
        populate_dummy(stk, BOOK)
    else:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, BOOK, 1)
        PRINT_DBG(stk.fig.entries[BOOK])

    # Retrieve Total Debt/Equity
    PRINT_DBG("Total Debt/Equity")
    pattern = re.compile(r'Total Debt/Equity')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, DtoE, 1)
        PRINT_DBG(stk.fig.entries[DtoE])

############# FIGURES ##################
    return stk

#Print Stock Info
def print_stock_info(stk):
    PRINT("Name: %r" %(stk.bscs.name))
    PRINT("Symbol: %r" %(stk.bscs.symbol))
    PRINT("Price: %r" %(stk.bscs.price))
    PRINT("Face Value: %r" %(stk.bscs.face_value))
    PRINT("Promoter Stake: %r" %(stk.bscs.promoter_stake))
    PRINT("Corporate Stake: %r" %(stk.bscs.corp_stake))
    PRINT("Public Stake: %r" %(stk.bscs.pub_stake))
    PRINT("FII Stake: %r" % (stk.bscs.fii_stake))
    PRINT("DII Stake: %r" % (stk.bscs.dii_stake))
    PRINT("Others Stake: %r" % (stk.bscs.others_stake))

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
    g1 = round(((last/first)**(1/years)-1), 2) * years / 10
    #g2 = round(((last/mid)**(1/mid_len)-1), 2) * mid_len / 10
    return g1
    #return min(g1,g2)

# Calcuate numbers
def calculate_numbers(stk):
    growth  = [0] * (GROWTH_PARAMS)
    fig = stk.fig
    i = 0
    stk.fig.sales_growth  = growth[i]  = calculate_growth(fig, SALES)
    i+=1
    stk.fig.profit_growth = growth[i] = calculate_growth(fig, PAT)
    i+=1
    stk.fig.cash_growth   = growth[i]   = calculate_growth(fig, CASH)
    i+=1
    stk.fig.book_growth   = growth[i]   = calculate_growth(fig, BOOK)
    PRINT_DBG("Growth of entries: %r"%(growth))
    try:
        stk.fig.growth = min(i for i in growth if i > 0)
    except ValueError:
        stk.fig.growth = 0

    # Calculating 20 years future earnings
    # High growth period
    stk.num.growth_1to5 = stk.fig.growth
    # Decremental growth period
    stk.num.growth_6to8 = round(stk.num.growth_1to5 * gr6to8_percent, 2)
    stk.num.growth_9to10 = round(stk.num.growth_6to8 * gr9to10_percent, 2)
    # Terminal growth
    stk.num.growth_11to15 = round(stk.num.growth_9to10 * gr11to15_percent, 2)
    stk.num.growth_16to20 = round(stk.num.growth_11to15 * gr16to20_percent, 2)
    PRINT("Growth Rates")
    PRINT("1-5 : {0:.2%}" .format(stk.num.growth_1to5))
    PRINT("6-8 : {0:.2%}" .format(stk.num.growth_6to8))
    PRINT("9-10 : {0:.2%}" .format(stk.num.growth_9to10))
    PRINT("11-15 : {0:.2%}" .format(stk.num.growth_11to15))
    PRINT("16-20 : {0:.2%}" .format(stk.num.growth_16to20))

    eps = stk.fig.ttm_eps
    growth = stk.num.growth_1to5
    discount = stk.num.discount_rate
    stk.num.eps_20yr=[]

    PRINT("EPS: %r"%(eps))
    PRINT("growth: %r"%(growth))
    PRINT("discount: %r"%(discount))
    for i in range(5):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(round(eps,2))
    PRINT(stk.num.eps_20yr)
    growth = stk.num.growth_6to8
    PRINT("growth: %r" % (growth))
    for i in range(5,8):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(round(eps,2))

    PRINT(stk.num.eps_20yr)
    growth = stk.num.growth_9to10
    PRINT("growth: %r" % (growth))
    for i in range(8,10):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(round(eps,2))
    PRINT(stk.num.eps_20yr)
    growth = stk.num.growth_11to15
    PRINT("growth: %r" % (growth))
    for i in range(10,15):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(round(eps,2))

    PRINT(stk.num.eps_20yr)
    growth = stk.num.growth_16to20
    PRINT("growth: %r" % (growth))
    for i in range(15,20):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(round(eps,2))

    PRINT("20 yrs yearly EPS: %r"%(stk.num.eps_20yr))
    PRINT("EPS after 5 years  : %r " % (round(stk.num.eps_20yr[4],2)))
    PRINT("EPS after 10 years : %r " % (round(stk.num.eps_20yr[9],2)))
    PRINT("EPS after 20 years : %r " % (round(stk.num.eps_20yr[19],2)))
    PRINT("Earnings for 5 years  : %r " % (round(sum(stk.num.eps_20yr[0:4]),2)))
    PRINT("Earnings for 10 years : %r " % (round(sum(stk.num.eps_20yr[0:9]),2)))
    PRINT("Earnings for 20 years : %r " % (round(sum(stk.num.eps_20yr),2)))
    #PRINT("Len : %r" %(len(stk.num.eps_20yr)))

    sym = u"\u20B9"
    tot_eps = sum(stk.num.eps_20yr)
    if tot_eps <= 0:
        tot_eps = 0
        stk.num.inflated_eps_price = 0
        stk.num.dcf_price = 0
        stk.num.cp_return_rate = 0
        stk.num.dcf_return_rate = 0
    else:
        stk.num.inflated_eps_price = tot_eps * ((1 - stk.num.inflation) ** 20)
        stk.num.dcf_price = round(stk.num.inflated_eps_price * 0.5, 2)
        stk.num.cp_return_rate = ((tot_eps/stk.bscs.price) ** (1/20)) - 1
        stk.num.dcf_return_rate = (tot_eps/stk.num.dcf_price) ** (1/20) - 1
        PRINT("Earnings for 20 years at %r percent inflation: %s%r" %(stk.num.inflation*100, sym, stk.num.inflated_eps_price))
        PRINT("Price at 50 percent MoS: %s%r" %(sym, stk.num.dcf_price))
        PRINT("Current Price: %s%r" %(sym, stk.bscs.price))
        PRINT("Return Rate at Current Price: {0:.2%}" .format(stk.num.cp_return_rate))
        PRINT("Return Rate at MoS Price: {0:.2%}" .format(stk.num.dcf_return_rate))

    if stk.bscs.price <= stk.num.dcf_price or stk.num.cp_return_rate > 0.09:
        write_to_excel(stk)

#Return a html page for a given URL
def get_html(url):
    return open(url)
    #return open("./log.html")
    #return open("./manpasand.html")
    #return open("./html_pages/YES BANK LTD..html")
    #return open("./html_pages/ADF FOODS LTD. .html")

#    #open with GET method
#    resp=requests.get(url)
#
#    #http_respone 200 means OK status
#    assert resp.status_code!=200,"Failed to open Web Page"
#
#    return resp.text

# Get stock information of "stock_name"
def get_stock_info(stock_page):
    html = open(stock_page)
    stk = populate_stock(html)
    html.close()
    return stk


def main():
#    files = glob.glob("./html_pages/*")
#    #files = glob.glob("./html_pages/WELSPUN INDIA LTD..html")
#    #files = glob.glob("./html_pages/LT FOODS LTD..html")
#    #files = glob.glob("./html_pages/SETCO AUTOMOTIVE LTD..html")
#    #files = glob.glob("./html_pages/WELSPUN INDIA LTD..html")
#    for stock_page in files:
#        print(stock_page)
#        stock = get_stock_info(stock_page)
#        if not stock:
#            continue
#        if stock.bscs.volume < 50000:
#            continue
#        if stock.bscs.price < 1:
#            continue
#        print_stock_info(stock)
#        stock.num.inflation = 0.08
#        stock.num.discount_rate = 0.0
#        stock.num.margin_of_safety = 0.5
#        calculate_numbers(stock)
#        stock=None

     get_all_stocks_html()

main()

#def news():
#    # the target we want to open
#    url='http://www.ratestar.in/company/daawat/532783/LT-Foods-Ltd-132783'
#
#    #open with GET method
#    resp=requests.get(url)
#
#    #http_respone 200 means OK status
#    if resp.status_code==200:
#        PRINT_DBG("Successfully opened the web page")
#
#        # we need a parser,Python built-in HTML parser is enough .
#        soup=BeautifulSoup(resp.text,'html.parser')
#
#        # l is the list which contains all the text i.e news
#        #l=soup.find("ul",{"class":"searchNews"})
#        #l=soup.body.find('div', attrs={'class':'lblCompany'}).text
#        l=soup.find(id='lblLTP').get_text()
#        PRINT_DBG(l)
#
##        #now we want to PRINT_DBG only the text part of the anchor.
##        #find all the elements of a, i.e anchor
##        for i in l.findAll("a"):
##            PRINT_DBG(i.text)
#    else:
#        PRINT_DBG("Error")
#
#news()

