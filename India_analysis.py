import glob

import excel
import DB
from common import *

def get_all_stocks_html():
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
#    with open("missing_files.txt") as f:
#        for line in f:
#            line = line.replace("\n","")
#            print(line)
#            get_stock_page(line)

    for i in range(0,sheet.nrows):
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
    try:
        for i in range(len(stk.fig.entries[PBT])):
            entry.append(round(stk.fig.entries[PBT][i] - stk.fig.entries[TAX][i],2))
    except IndexError:
        return
    except TypeError:
        return
    stk.fig.entries.insert(PAT, entry)
    PRINT_DBG("PAT:")
    PRINT_DBG(stk.fig.entries[PAT])

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

        val = div2.get_text().lstrip().rstrip().replace(",","").replace("%","")
        #If the value is valid? append else skip
        if convert == 1:# and str_to_float_valid(val):
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
    #stk.fig.entries[row] = entry.copy()
    #stk.fig.entries.append(entry)
    stk.fig.entries.insert(row, entry)
    #PRINT_DBG("Entries:")
    #PRINT_DBG(stk.fig.entries[row])

    #stk.fig.fig_years.append(i)
    #stk.fig.fig_years.insert(row, i)
    #PRINT_DBG("Years : %r" % (stk.fig.fig_years[row]))

#Print Stock Info
def print_stock_info(stk):
    PRINT("Name: %r" %(stk.bscs.name))
    PRINT("Symbol: %r" %(stk.bscs.symbol))
    PRINT("Price: %r" %(stk.bscs.price))
    PRINT("Face Value: %r" %(stk.bscs.face_value))
    PRINT("Promoter Stake: %r" %(stk.bscs.promoter_stake))
    PRINT("Corporate Stake: %r" %(stk.bscs.corp_stake))
    PRINT("Public Stake: %r" %(stk.bscs.pub_stake))
    PRINT("conf.FII Stake: %r" % (stk.bscs.fii_stake))
    PRINT("conf.DII Stake: %r" % (stk.bscs.dii_stake))
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

# Calcuate numbers
def calculate_dcf(com, ash, stk):
#    global conf.COUNT
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
    print("Growth of entries: %r"%(growth))
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
        PRINT("Earnings for 20 years at %r percent inflation: %s%r" %(stk.num.inflation*100, RUPEE, stk.num.inflated_eps_price))
        PRINT("Price at 50 percent MoS: %s%r" %(RUPEE, stk.num.dcf_price))
        PRINT("Current Price: %s%r" %(RUPEE, stk.bscs.price))
        PRINT("Return Rate at Current Price: {0:.2%}" .format(stk.num.cp_return_rate))
        PRINT("Return Rate at MoS Price: {0:.2%}" .format(stk.num.dcf_return_rate))

    #if stk.bscs.price <= stk.num.dcf_price or stk.num.cp_return_rate > 0.09:
    conf.COUNT+=1
    write_to_excel(com, ash, stk)
    return True

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

def open_db(db_name):
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client[db_name]
    return db

def write_to_collection(col, doc):
    if col.find({"bscs.symbol":doc['bscs']['symbol']}).count() > 0 :
        print("Stock exists")
        return
    col.insert_one(doc)
    print("Count: %r" %(col.count()))
    #x = col.find_one()
    #print(x)

# Fetches symbol name from BSE_Stocks.xls file
# for BSE symbol and updates the "sample" collection
# Test API. Not used often
def update_db_symbol_id():
    db = open_db('Stocks')
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    sheet.cell_value(0,0)
    for i in range(1,2):
    #for i in range(1,sheet.nrows):
        print("%r: %s : %s" %(i, str(int(sheet.cell_value(i, 0))), sheet.cell_value(i,1)))
        sym = str(int(sheet.cell_value(i, 0)))
        sym_id = sheet.cell_value(i, 1)
        collection = db['sample']
        sym="505075"
        collection.update({"bscs.bse_symbol": sym},
                {"$set": {"bscs.symbol": sym_id}})

# Populates all html file names in a file
def build_files(files):
    f = open("files.txt", "w")
    for stock in files:
        f.write(stock)
        f.write("\n")
    f.close()

def build_database(files):
    db = open_db('Stocks')
    #db.Indian_Stocks.drop()
    f = open("files.txt", "r")

    for i, stock_page in enumerate(f):
        if i > -1:

            print("%d: %s" %(i, stock_page))
            stock = get_stock_info(stock_page.replace("\n",""))
            if not stock:
                PRINT_ERR("Unable to get stock info of %s" %(stock_page))
                continue
#           val = internet.get_LTP('India', stock.bscs.symbol)
#           if val == -1:
#               PRINT_ERR("Unable to get LTP for %s"%(stock.bscs.name))
#           else:
#               stock.bscs.price = val

            obj = build_json_object(stock)
            write_to_collection(db['Indian_Stocks'], obj)
            stock = None
            obj   = None

#Find missing entries in the db.
# Compare with entries in BSE_Stocks.xls
def find_files():
    db = open_db('Stocks')
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    f = open("missing_files.txt", "w")
    for i in range(1,sheet.nrows):
        obj = db.Indian_Stocks.find({"bscs.symbol":sheet.cell_value(i, 1)})
        if obj.count() == 0:
            print("%s Not found"%(sheet.cell_value(i, 2)))
            f.write(sheet.cell_value(i, 2))
            f.write("\n")

    f.close()


def main():
#    find_files()
#    update_db_symbol_id()
#    files = glob.glob("./html_pages/*")
    files = glob.glob("./India_Stocks/html_pages/Sanofi India Ltd.html")
#    files = glob.glob("./html_pages/FILATEX INDIA LTD. .html")
#    files = glob.glob("./html_pages/Krishna Capital and Securities Ltd.html")
#    files = glob.glob("./html_pages/STERLING TOOLS LTD. .html")
#    files = glob.glob("./html_pages/WELSPUN INDIA LTD..html")
#    files = glob.glob("./html_pages/LT FOODS LTD..html")
#    files = glob.glob("./html_pages/PIDILITE INDUSTRIES LTD..html")
#    files = glob.glob("./html_pages/SETCO AUTOMOTIVE LTD..html")
#    #files = glob.glob("./html_pages/WELSPUN INDIA LTD..html")
#
    i=0
    j=0
#
    #build_files(files)
    # Add stock info to the database
    DB.build_India_database(files, 'COLD')
    return
#
    # All Stocks Excel File
    all_stk = xlwt.Workbook()
    ash = all_stk.add_sheet("All Stocks")
    excel.add_dcf_header(ash)

    for stock_page in files:
        print(stock_page)
        stock = get_India_stock_info(stock_page)
        if not stock:
            continue
        #if stock.bscs.volume < 50000:
        #    continue
        if stock.bscs.price < 1:
            continue
        stock.bscs.price = internet.get_LTP('India', stock.bscs.symbol)
        print_stock_info(stock)
        stock.num.inflation = 0.08
        stock.num.discount_rate = 0.0
        stock.num.margin_of_safety = 0.5
        #Company Excel File
        com = xlwt.Workbook()
        calculate_dcf(com, ash, stock)
        excel = "./India_Stocks/excel_files/%s.xls" % (stock.bscs.name)
        PRINT("Writing to %s" % (excel))
        com.save(excel)
        j+=1

        stock=None
        com=None
        i+=1

    print("Stocks Calculated: %r" %(i))
    print("Stocks DCF Eligible: %r" %(j))
    now = datetime.datetime.now()
    excel = "./India_Stocks/DCF_Calc/All_Stocks_%s.xls" % (str(now))
    print("Saving DCF stocks to %s"%(excel))
    all_stk.save(excel)
#    #all_stk.save("excel_files/All_Stocks.xls")
#    get_all_stocks_html()

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

