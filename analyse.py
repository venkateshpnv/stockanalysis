import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests 
from bs4 import BeautifulSoup 

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
        self.ttm_eps = 0
        # Long Term Debt
        self.lt_debt = 0

        # sales info
        self.ttm_sales  = 0
        self.past_sales = 0
        self.mid_sales  = 0
        self.sales_growth = 0

        # profit info
        self.ttm_profit  = 0
        self.past_profit = 0
        self.mid_profit  = 0
        self.profit_growth = 0

        # cash flow info
        self.ttm_cash  = 0
        self.past_cash = 0
        self.mid_cash  = 0
        self.cash_growth = 0

        self.ttm_book  = 0
        self.past_book = 0
        self.mid_book  = 0
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
        self.eps_20yr = []
       
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
    
    # Promoter Stake
    divTag = soup.find_all("div", {"class": "col-md-6", "align": "left"})
    for tag in divTag:
        div2 = tag.find_all("div", {"class": "com-mid-share-table"})
        for tag2 in div2:
            div3 = tag.find("div", {"class": "float-lt com-mid-share-tab2"})
            print("1")
            for lis in div3:
                print("2")
                for li in lis:
                    print("3")
                    print(li.text)
#    l=soup.find(id='lblLTP').get_text()
#    stk.bscs.price = l
    
    # Face Value
    l=soup.find(id='lblFaceValue').get_text()
    stk.bscs.face_value = l

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

# Get stock information from the URL
def get_stock_info():
    html = get_html("hello")
    stk = populate_stock(html)
    print_stock_info(stk)

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

