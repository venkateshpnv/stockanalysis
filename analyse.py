import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests 
from bs4 import BeautifulSoup 

YEARS  = 0
SALES  = 1
PROFIT = 2
CASH   = 3
BOOK   = 4

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
    def __init(self):
        self.years = 10
        self.ttm_eps = 0
        # Long Term Debt
        self.lt_debt = 0

        # row 0 - year
        # row 1 - sales
        # row 2 - profit
        # row 3 - free cash flow
        # row 4 - book value
        self.figures = [[0] * self.years  for i in range(5)] # ten years of sales
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0

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
    #print(divTag)
    divTag2 = divTag.find("div", {"class" : "float-lt com-mid-share-tab2", "align" : "right"})
    #print(divTag2)
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
    #populate(years, YEARS)

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
    #populate(div, SALES)

    # Retrieve Profit After Taxes
    for i in range(26):
        div = div.find_next("div", {"class": "CHead"})
    #populate(div, PROFIT)
    #f = open("profit.html", "w")
    #f.write(str(div.prettify()))
    #f.close()

    # Retrieve TTM EPS
    for i in range(5):
        div = div.find_next("div", {"class": "CHead"})
    stk.fig.ttm_eps = div.find(id='TTM_EPS').get_text()
    print(stk.fig.ttm_eps)

    sales = annual_cons.find("div", {"class": "in-tab-col4", "style":"font-weight: 600", "align":"left"})
    #populate(sales, SALES)

    profit = annual_cons.find("div", {"class": "accordion-toggle", "style": "width: 100", "align": "left"})
    #profit = annual_cons.find("div", {"class": "in-tab-col4", "style":"font-weight:bold", "align":"left"})
    #print(profit)
############# FIGURES ################## 
#    for tag in divTag:
#        div2 = tag.find_all("div", {"class": "com-mid-share-table"})
#        for tag2 in div2:
#            div3 = tag.find("div", {"class": "float-lt com-mid-share-tab2"})
#            #print(div3.text)
#            print(1)
#            for lis in div3:
#                li = lis.find("li")
#                #print(lis.text)
##    l=soup.find(id='lblLTP').get_text()
##    stk.bscs.price = l
    
#        #now we want to print only the text part of the anchor. 
#        #find all the elements of a, i.e anchor 
#        for i in l.findAll("a"): 
#            print(i.text) 
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

