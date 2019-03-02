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
        self.growth = 0
        #self.entries = [0]
        #self.fig_years = [0]

class Numbers:
    # figures in percentages
    discount_rate = 0
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
    #print(stk.fig.entries[row])

    stk.fig.fig_years.append(i)
    #print(stk.fig.fig_years[row])

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
    stk.bscs.price = float(l)
 
    # Face Value
    l=soup.find(id='lblFaceValue').get_text()
    stk.bscs.face_value = l

    #soup=BeautifulSoup(html_page,'lxml')     
    # Promoter Stake
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

    # Retrieve TTM EPS
    for i in range(5):
        div = div.find_next("div", {"class": "CHead"})
    stk.fig.ttm_eps = float(div.find(id='TTM_EPS').get_text())

    # Retrieve Operating Cash Flow
    cash_flow = soup.find("table", {"id": "tbl_CashFlowCons"})
    tr = cash_flow.findNext("tr")
    tr = tr.findNext("tr")
    div = tr.find("div", {"class": "CHead"})
    populate(stk, div, CASH, 1)

    # Retrieve Book Value
    book_value = soup.find("section", {"id": "Financial"})
    tr = book_value.findNext("tr")
    for i in range(5):
        tr = tr.findNext("tr")
    div = tr.find("div", {"class": "CHead"})
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
    print_stock_info(stk)
    return stk

def calculate_growth(fig, row):
    years = fig.fig_years[row]
    first = fig.entries[row][0]
    last  = fig.entries[row][years-1]
    return (last/first)**(1/years)-1

# Calcuate numbers
def calculate_numbers(stk, disc_rate):
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
    stk.num.growth_6to8 = stk.num.growth_1to5 * 0.7
    stk.num.growth_9to10 = stk.num.growth_6to8 * 0.8
    # Terminal growth
    stk.num.growth_11to15 = stk.num.growth_9to10 * 0.5
    stk.num.growth_16to20 = stk.num.growth_11to15 * 0.8
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

def main():
    stock = get_stock_info()
    calculate_numbers(stock, 8)

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

