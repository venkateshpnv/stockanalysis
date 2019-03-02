import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests 
from bs4 import BeautifulSoup 

MAX_YEARS = 20

YEARS  = 0
SALES  = 1
PROFIT = 2
CASH   = 3
BOOK   = 4

# Number of figures we are tracking data for.
# Update this if you add new entries
indices = 5

class Basics:
    def __init__(self):
        self.name   = 'DEADCOW'
        self.symbol = 'DEAD'
        self.price  = 0
        self.promoter_stake = 0
        self.pub_stake      = 0
        self.face_value     = 0

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
        #self.entries = [0]
        #self.fig_years = [0]

class Numbers:
    def __init__(self):
        # figures in percentages
        self.discount_rate = 0
        self.growth_1to5   = 0
        self.growth_6to8   = 0
        self.growth_9to10  = 0
        self.growth_11to15 = 0
        self.growth_16to20 = 0

        # current eps
        self.eps = 0
        # Total earnings for 20 yrs
        self.eps_20yr = [0] * 20
       
        # start and end years
        self.fig_yr  = 2018
        self.cur_yr  = 2019
        self.term_yr = 2029

        # DCP price and return rate
        self.dcf_price = 0
        self.margin_of_safety = 0
        # return rate at DCF price
        self.dcf_return_rate  = 0
        # return rate at current price
        self.cp_return_rate   = 0

class Stock:
    def __init__(self):
        self.name = "Hello"
        self.bscs = Basics()
        self.fig  = Figures()
        self.num  = Numbers()

def populate(stk, div, row, convert):
    entry = []
    f = open("figs.html", "w")
    st = "############################## Row %r #######################" %(row)
    f.write(st)
    f.write(str(div.prettify()))
    f.close()

    i = 0
    div_tags = div.find_all("div")
    for tag in div_tags:
        entry.append(tag.get_text().lstrip().rstrip().replace(",", ""))
        i += 1

    entry.reverse()
    if convert:
        entry = list(map(float, entry))
    stk.fig.entries.append(entry)
    print(stk.fig.entries[row])

    stk.fig.fig_years.append(i)
    print(stk.fig.fig_years[row])

def populate_stock(html_page):
    stk = Stock()
    # we need a parser,Python built-in HTML parser is enough . 
    soup=BeautifulSoup(html_page,'html.parser')      
    # l is the list which contains all the text i.e news 
    #l=soup.find("ul",{"class":"searchNews"}) 
    #l=soup.body.find('div', attrs={'class':'lblCompany'}).text

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
    stk.bscs.price = l
 
    # Face Value
    l=soup.find(id='lblFaceValue').get_text()
    stk.bscs.face_value = l

    #soup=BeautifulSoup(html_page,'lxml')     
    # Promoter Stake
    #divTag = soup.find("div", {"class": "col-md-6", "align": "left"})
    divTag = soup.find("div", {"class": "com-mid-share-wrap", "align": "right"})
    divTag2 = divTag.find("div", {"class" : "float-lt com-mid-share-tab2", "align" : "right"})
    pshare = divTag2.ul.li.get_text()
    stk.bscs.promoter_stake = pshare.lstrip()

    pshare = divTag2.ul.li.find_next_sibling("li").find_next_sibling("li").get_text()
    stk.bscs.pub_stake = pshare.lstrip()
############# BASICS ##################


############# FIGURES ################## 
    annual_cons = soup.find("table", {"id": "tblAnnualCons", "class": "table table-bordered table-striped"})
    #print(annual_cons)
    #f = open("annual_cons.html", "w")
    #f.write(str(annual_cons.prettify()))
    #f.close()

    tr = annual_cons.findNext("tr")
    years = tr.find("div", {"class": "in-tab-main-wrap"})
    years = years.find("div", {"class": "CHead"})
    populate(stk, years, YEARS, 0)

    #years = annual_cons.find("div", {"class": "in-tab-main-wrap"})
    #print(years)
    #f = open("years.html", "w")
    #f.write(str(years.prettify()))
    #f.close()

    tr = tr.findNext("tr")
    #tr = annual_cons.tr.find_next_sibling("tr")
    #print(tr)
    #f = open("tr.html", "w")
    #f.write(str(tr.prettify()))
    #f.close()

    # Retrieve Sales
    div = tr.find("div", {"class": "CHead"})
    populate(stk, div, SALES, 1)

    # Retrieve Profit After Taxes
    for i in range(26):
        div = div.find_next("div", {"class": "CHead"})
    populate(stk, div, PROFIT, 1)
    #f = open("profit.html", "w")
    #f.write(str(div.prettify()))
    #f.close()

    # Retrieve TTM EPS
    for i in range(5):
        div = div.find_next("div", {"class": "CHead"})
    stk.fig.ttm_eps = div.find(id='TTM_EPS').get_text()
    print(stk.fig.ttm_eps)

    # Retrieve Operating Cash Flow
    cash_flow = soup.find("table", {"id": "tbl_CashFlowCons"})
    #print(cash_flow)
    #f = open("cash.html", "w")
    #f.write(str(cash_flow.prettify()))
    #f.close()

    tr = cash_flow.findNext("tr")
    tr = tr.findNext("tr")
    #print(tr)
    #f = open("cash2.html", "w")
    #f.write(str(tr.prettify()))
    #f.close()
    div = tr.find("div", {"class": "CHead"})
    #print(div)
    populate(stk, div, CASH, 1)

    # Retrieve Book Value
    book_value = soup.find("section", {"id": "Financial"})
    #print(book_value)
    #f = open("book.html", "w")
    #f.write(str(book_value.prettify()))
    #f.close()

    tr = book_value.findNext("tr")
    for i in range(5):
        tr = tr.findNext("tr")
    #print(tr)
    #f = open("book2.html", "w")
    #f.write(str(tr.prettify()))
    #f.close()
    div = tr.find("div", {"class": "CHead"})
    #print(div)
    populate(stk, div, BOOK, 1)

############# FIGURES ################## 

    return stk

#Return a html page for a given URL
def get_html(url):
    return open("./log.html")

#    #open with GET method 
#    resp=requests.get(url) 
#
#    #http_respone 200 means OK status 
#    assert resp.status_code!=200,"Failed to open Web Page" 
#
#    return resp.text

#Print Stock Info
def print_stock_info(stk):
    print("Name: %r" %(stk.bscs.name))
    print("Symbol: %r" %(stk.bscs.symbol))
    print("Price: %r" %(stk.bscs.price))
    print("Face Value: %r" %(stk.bscs.face_value))
    print("Promoter Stake: %r" %(stk.bscs.promoter_stake))
    print("Public Stake: %r" %(stk.bscs.pub_stake))

# Get stock information from the URL
def get_stock_info():
    html = get_html("hello")
    stk = populate_stock(html)
    #print_stock_info(stk)

get_stock_info()

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

