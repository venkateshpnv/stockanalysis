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

MAX_YEARS = 20

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

# Percentage change in growth over a period of time
gr1to5_percent   = 1
gr6to8_percent   = 0.8
gr9to10_percent  = 0.7
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
    fig_years = []

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
        self.fig_years = [0 for i in range(indices)]

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

    sheet = wb.add_sheet(stk.bscs.name)

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
    sheet.write(i, 1, stk.bscs.price/stk.fig.ttm_eps)


    i = 10 #row 11
    sheet.write(i, 0, "Growth Rate(1-5 Years)")
    sheet.write(i, 1, stk.num.growth_1to5, style_percent)

    i += 1 #row 12
    sheet.write(i, 0, "Growth Rate(6-8 Years)")
    # TODO replace 0.7, 0.8 with variables.
    sheet.write(i, 1, Formula("B11 * 0.7"), style_percent)

    i += 1 #row 13
    sheet.write(i, 0, "Growth Rate(9-10 Years)")
    sheet.write(i, 1, Formula("B12 * 0.8"), style_percent)

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

    wb.save("DCF.xls")

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
    #print(str(html_src))

    if driver.current_url == old_url:
        print("Unable to parse %r" %(stock))
        f = open("unparsed_stocks.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        #print("Found stock %r" %(stock))
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
#        print("Unable to parse %r" %(stock))
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
    for i in range(3934,sheet.nrows):
    #for i in range(1,10):
        print("%r: %r" %(i, sheet.cell_value(i, 2)))
        get_stock_page(sheet.cell_value(i,2))
        
#    f = open('NSE_Stocks.csv')
#    #f = open('BSE_Stocks.csv')
#    csv_f = csv.reader(f)
#    for row in csv_f:
#        print(row)
#        #print(row[1])
#        #print(row[0], row[1], row[2],)

def calculate_PAT(stk):
    entry=[]
    for i in range(stk.fig.fig_years[PBT]):
        entry.append(round(stk.fig.entries[PBT][i] - stk.fig.entries[TAX][i],2))
    stk.fig.entries.insert(PBT, entry)
    print("PAT:")
    print(stk.fig.entries[PBT])

def populate(stk, div, row, convert):
    entry = []
    #f = open("figs.html", "w")
    #st = "############################## Row %r #######################" %(row)
    #f.write(st)
    #f.write(str(div.prettify()))
    #f.close()

    i = 0
    div2 = div.find_next("div")
    #print(div2)

    while True:
        c = str(div2['class'])
        # If end of class? stop
        if c == "['clear']":
            #print("Found Clear Class")
            break
        # If html page does not display? skip
        if div2.has_attr("style"):
            #print("Has attr style")
            style = str(div2['style'])
            #print("Style : %r " %(style))
            if style == 'display: none;':
                print("Skipping: %r" %(div2))
                div2 = div2.find_next("div")
                print("Next: %r" %(div2))
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
    #print("Entries:")
    #print(stk.fig.entries[row])

    #stk.fig.fig_years.append(i)
    stk.fig.fig_years.insert(row, i)
    #print("Years : %r" % (stk.fig.fig_years[row]))
    print("************* Returning *******************")

def populate_item(stk, pattern, annual_cons, row, convert):
    div = annual_cons.find("div",
                           text=pattern)
    div = div.parent
    div = div.find_next("div", {"class": "CHead"})
    populate(stk, div, row, convert)

def populate_stock(html_page):
    stk = Stock()
    # we need a parser,Python built-in HTML parser is enough . 
    soup=BeautifulSoup(html_page,'html.parser')      
    # l is the list which contains all the text i.e news 

############# BASICS ##################
    #Company Name
    l=soup.find(id='lblCompany').get_text()
    stk.bscs.name = l

    # Ticker
    l=soup.find(id='lblNSE').get_text()
    l = l.split(": ", 1)[1]
    stk.bscs.symbol = l

    # Price
    l=soup.find(id='lblLTP').get_text()
    stk.bscs.price = str_to_float(l)
 
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

    stk.bscs.volume = l
    print("Volume %r" %(stk.bscs.volume))

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
    if not annual_cons:
        print("No Consolidated results. Checking for standalone results")
        annual_cons = annual.find("table", {"id": "tblAnnualStd", "class": "table table-bordered table-striped"})
        if not annual_cons:
            print("No Standalone results. Checking Annual")
            annual_cons = annual.find("table", {"id": "tblAnnual", "class": "table table-bordered table-striped"})
            if not annual_cons:
                assert "No Annual Results found"

    #Years
    print("YEARS: %r" %(YEARS))
    pattern = re.compile(r'Description\n')
    populate_item(stk, pattern, annual_cons, YEARS, 0)
    print(stk.fig.entries[YEARS])
    #Sales
    print("SALES: %r"%(SALES))
    pattern = re.compile(r'Net Sales')
    populate_item(stk, pattern, annual_cons, SALES, 1)
    print(stk.fig.entries[SALES])
    #Profit Before Taxes
    print("PBT: %r" %(PBT))
    pattern = re.compile(r'PBT\n')
    populate_item(stk, pattern, annual_cons, PBT, 1)
    print(stk.fig.entries[PBT])
    #Tax
    print("TAX: %r" %(TAX))
    pattern = re.compile(r'Tax\n')
    populate_item(stk, pattern, annual_cons, TAX, 1)
    print(stk.fig.entries[TAX])

    print("PAT: %r" %(PAT))
    calculate_PAT(stk)

    #EPS
    print("EPS: %r, indices: %r" %(EPS, indices))
    pattern = re.compile(r'Unadjusted EPS\n')
    populate_item(stk, pattern, annual_cons, EPS, 1)
    print(stk.fig.entries[EPS])

    stk.fig.ttm_eps = stk.fig.entries[EPS-1][-1]
    print("TTM EPS: %r" %(stk.fig.ttm_eps))

    # Retrieve Operating Cash Flow
    print("Cash Flow")
    cash = soup.find("section", {"id":"Cash"})
    f = open("man_cash.html", "w")
    f.write(cash)
    f.close()
    cash_flow = cash.find("table", {"id": "tbl_CashFlowCons"})
    if not cash_flow:
        cash_flow = cash.find("table", {"id": "tbl_CashFlowStd"})
        if not cash_flow:
            cash_flow = cash.find("table", {"id": "Cash"})
            assert "No Cash Flow numbers"
    #print(cash_flow)
    tr = cash_flow.findNext("tr")
    tr = tr.findNext("tr")
    div = tr.find("div", {"class": "CHead"})
    populate(stk, div, CASH, 1)

    # Retrieve Book Value
    print("Book Value")
    book_value = soup.find("section", {"id": "Financial"})
    tr = book_value.findNext("tr")
    for i in range(5):
        tr = tr.findNext("tr")
    div = tr.find("div", {"class": "CHead"})
    populate(stk, div, BOOK, 1)

############# FIGURES ################## 

    return stk

#Print Stock Info
def print_stock_info(stk):
    print("Name: %r" %(stk.bscs.name))
    print("Symbol: %r" %(stk.bscs.symbol))
    print("Price: %r" %(stk.bscs.price))
    print("Face Value: %r" %(stk.bscs.face_value))
    print("Promoter Stake: %r" %(stk.bscs.promoter_stake))
    print("Corporate Stake: %r" %(stk.bscs.corp_stake))
    print("Public Stake: %r" %(stk.bscs.pub_stake))
    print("FII Stake: %r" % (stk.bscs.fii_stake))
    print("DII Stake: %r" % (stk.bscs.dii_stake))
    print("Others Stake: %r" % (stk.bscs.others_stake))

def calculate_growth(fig, row):
    years = fig.fig_years[row]
    first = fig.entries[row][0]
    last  = fig.entries[row][years-1]
    return (last/first)**(1/years)-1

# Calcuate numbers
def calculate_numbers(stk):
    growth  = [0] * (indices-1)
    fig = stk.fig

    stk.fig.sales_growth  = growth[SALES-1]  = calculate_growth(fig, SALES)
    stk.fig.profit_growth = growth[PROFIT-1] = calculate_growth(fig, PROFIT)
    stk.fig.cash_growth   = growth[CASH-1]   = calculate_growth(fig, CASH)
    stk.fig.book_growth   = growth[BOOK-1]   = calculate_growth(fig, BOOK)
    stk.fig.growth = min(growth)
    #print(growth)

    # Calculating 20 years future earnings
    # High growth period
    stk.num.growth_1to5 = stk.fig.growth
    # Decremental growth period
    stk.num.growth_6to8 = stk.num.growth_1to5 * gr6to8_percent
    stk.num.growth_9to10 = stk.num.growth_6to8 * gr9to10_percent
    # Terminal growth
    stk.num.growth_11to15 = stk.num.growth_9to10 * gr11to15_percent
    stk.num.growth_16to20 = stk.num.growth_11to15 * gr16to20_percent
    print("Growth Rates")
    print("1-5 : %r" %(stk.num.growth_1to5))
    print("6-8 : %r" %(stk.num.growth_6to8))
    print("9-10 : %r" %(stk.num.growth_9to10))
    print("11-15 : %r" %(stk.num.growth_11to15))
    print("16-20 : %r" %(stk.num.growth_16to20))

    eps = stk.fig.ttm_eps
    growth = stk.num.growth_1to5
    discount = stk.num.discount_rate

    print(eps)
    for i in range(5):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(eps)

    growth = stk.num.growth_6to8
    for i in range(5,8):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(eps)

    growth = stk.num.growth_9to10
    for i in range(8,10):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(eps)

    growth = stk.num.growth_11to15
    for i in range(10,15):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(eps)

    growth = stk.num.growth_16to20
    for i in range(15,20):
        eps = eps * ((1 + growth) / (1 + discount))
        stk.num.eps_20yr.append(eps)

    print("EPS after 5 years  : %r " % (stk.num.eps_20yr[4]))
    print("EPS after 10 years : %r " % (stk.num.eps_20yr[9]))
    print("EPS after 20 years : %r " % (stk.num.eps_20yr[19]))
    print("Earnings for 5 years  : %r " % (sum(stk.num.eps_20yr[0:4])))
    print("Earnings for 10 years : %r " % (sum(stk.num.eps_20yr[0:9])))
    print("Earnings for 20 years : %r " % (sum(stk.num.eps_20yr)))
    print("Len : %r" %(len(stk.num.eps_20yr)))

    tot_eps = sum(stk.num.eps_20yr)
    tot_eps = tot_eps * ((1 - 0.08) ** 20)
    print("Earnings for 20 years at 8 percent inflation: %r" %(tot_eps))
    print("Price at 50 percent MoS: %r" %(tot_eps * 0.5))
    stk.num.dcf_price = tot_eps * 0.5

    write_to_excel(stk)

#Return a html page for a given URL
def get_html(url):
    #return open("./log.html")
    return open("./manpasand.html")
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
def get_stock_info(stock_name):
    html = get_html("hello")
    stk = populate_stock(html)
    print_stock_info(stk)
    return stk


def main():
    stock_name = " "
    stock = get_stock_info(stock_name)
    return
    stock.num.inflation = 0.08
    stock.num.discount_rate = 0.0
    stock.num.margin_of_safety = 0.5
    calculate_numbers(stock)

#     get_all_stocks_html()

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
#        print("Successfully opened the web page") 
#    
#        # we need a parser,Python built-in HTML parser is enough . 
#        soup=BeautifulSoup(resp.text,'html.parser')     
#
#        # l is the list which contains all the text i.e news 
#        #l=soup.find("ul",{"class":"searchNews"}) 
#        #l=soup.body.find('div', attrs={'class':'lblCompany'}).text
#        l=soup.find(id='lblLTP').get_text()
#        print(l)
#    
##        #now we want to print only the text part of the anchor. 
##        #find all the elements of a, i.e anchor 
##        for i in l.findAll("a"): 
##            print(i.text) 
#    else: 
#        print("Error") 
#        
#news()

