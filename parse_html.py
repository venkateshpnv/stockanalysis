# Parsing HTML
from bs4 import BeautifulSoup 

#Yahoo Financials
#from yahoofinancials import YahooFinancials as yf

#Regular Expressions
import re

import internet
from datastructures import Stock
import excel
from common import *
from conf import *
import json_code
import DB
from datetime import datetime

def html_head():
    s = ''
    s += "%s\n" %('<style type="text/css">')
    s += "%s\n" %('.tg  {border-collapse:collapse;border-spacing:0;}')
    s += "%s\n" %('.tg td{font-family:Arial, sans-serif;font-size:14px;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;border-color:black;}')
    s += "%s\n" %('.tg th{font-family:Arial, sans-serif;font-size:14px;font-weight:normal;padding:10px 5px;border-style:solid;border-width:1px;overflow:hidden;word-break:normal;border-color:black;}')
    s += "%s\n" %('.tg .tg-0lax{text-align:left;vertical-align:top}')
    s += "%s\n" %('</style>')
    s += "%s\n" %('<table class=tg>')
    return s
 
def html_text(s, lol, col=None):
    for sublist in lol:
        s += "%s\n" %('  <tr>')
        if col:
            val= '<mark> ' + sublist[col] + ' </mark>'
            sublist[col] = val
        s += "%s\n" %('    </td><td class="tg-0lax">'.join(sublist))
        s += "%s\n" %('  </tr>')
    s += "%s\n" %('</table>')
    return s

def html_set_line(s):
    s += "%s\n" %('<hr />')
    return s

#def html_table(lol):
#    s = ''
#    s += "%s\n" %('<table>')
#    for sublist in lol:
#      s += "%s\n" %('  <tr><td>')
#      s += "%s\n" %('    </td><td>'.join(sublist))
#      s += "%s\n" %('  </td></tr>')
#    s += "%s\n" %('</table>')
#    return s

def get_soup(html_text):
    return BeautifulSoup(html_text, 'html.parser')

def get_entries(soup, pattern):
    entries = []
    l=soup.find(text=pattern)
    try:
        tags = l.parent.parent
    except AttributeError:
        #print("No entries")
        return entries

    l=tags.find_all("td")
    for i in range(1, len(l)):
        entries.append(str_to_float(l[i].get_text()))
    return entries

def get_debt(soup, pattern):
    entries = []
    l=soup.findAll(text=pattern)
    if not l:
        return entries
    try:
        if len(l) > 2:
            tags = l[2].parent.parent
            #print(tags)
            l=tags.find_all("td")
            for i in range(1, len(l)):
                entries.append(str_to_float(l[i].get_text()))
            return entries
    except AttributeError:
        return entries

def populate_India_entry(stk, div, row, convert):
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
    #stk['fig']['entries'][row] = entry.copy()
    #stk['fig']['entries'].append(entry)
    stk['fig']['entries'].insert(row, entry)
    #PRINT_DBG("Entries:")
    #PRINT_DBG(stk['fig']['entries'][row])

    #stk['fig']['fig_years'].append(i)
    #stk['fig']['fig_years'].insert(row, i)
    #PRINT_DBG("Years : %r" % (stk['fig']['fig_years'][row]))

def populate_India_item(stk, pattern, section, row, convert):
    div = section.find("div", text=pattern)
    if not div:
        PRINT_ERR("No Match")
        PRINT_ERR(pattern)
        return False
    div = div.parent
    div = div.find_next("div", {"class": "CHead"})
    populate_India_entry(stk, div, row, convert)
    PRINT_DBG(stk['fig']['entries'][row])
    return True

def populate_India_stock(html_page):
    stk = Stock()
    # we need a parser,Python built-in HTML parser is enough . 
    soup=BeautifulSoup(html_page,'html.parser')      
    # l is the list which contains all the text i.e news 

############# BASICS ##################
    #Company Name
    try:
        l=soup.find(id='lblCompany').get_text()
    except:
        PRINT_ERR("Unable to get Company name")
        return None
    stk['bscs']['name'] = l.lstrip().rstrip().replace(".","")
    print(stk['bscs']['name'])

    # Ticker
    l=soup.find(id='lblBSE').get_text()
    #l=soup.find(id='lblNSE').get_text()
    l = l.split(": ", 1)[1]
    stk['bscs']['bse_symbol'] = l
   
    excel.get_India_symbol_and_sector(stk)

    # Price
    l = internet.get_LTP('India', stk['bscs']['symbol'])
    try:
        stk['bscs']['price'] = l
        #stk['bscs']['price'] = str_to_float(l)
    except ValueError:
        stk['bscs']['price'] = 0
#    if stk['bscs']['price'] < 1:
#        PRINT_ERR("Price less than 1")
#        return None

    # Face Value
    l=soup.find(id='lblFaceValue').get_text()
    try:
        stk['bscs']['face_value'] = int(l)
    except ValueError:
        stk['bscs']['face_value'] = 10

    excel.get_India_stock_split_info(stk)

    # Volume
    l=soup.find(id='lblVolume').get_text()
    try:
        stk['bscs']['volume'] = int(l)
    except ValueError:
        stk['bscs']['volume'] = 0

#    if stk['bscs']['volume'] < 50000:
#        return None

    PRINT_DBG("Volume %r" %(stk['bscs']['volume']))

    #Market Cap
    try:
        l=soup.find(id='lblMCap').get_text()
    except:
        PRINT_ERR("Unable to get market cap")
        return None
    try:
        stk['bscs']['mcap'] = float(l.lstrip().rstrip().replace(",", ""))
    except ValueError:
        stk['bscs']['mcap'] = 0


    #soup=BeautifulSoup(html_page,'lxml')     
    # Promoter Stake
    divTag = soup.find("div", {"class": "com-mid-share-wrap", "align": "right"})
    divTag2 = divTag
    for i in range(7):
        divTag2 = divTag2.find_next("div")
    #divTag2 = divTag.find("div", {"class" : "float-lt com-mid-share-tab2", "align" : "right"})
    li = divTag2.ul.li
    pshare = li.get_text()
    stk['bscs']['promoter_stake'] = p2f(pshare.lstrip())
    li = li.find_next("li")
    # Corporate Stake
    pshare = li.get_text()
    stk['bscs']['corp_stake'] = p2f(pshare.lstrip())
    li = li.find_next("li")
    # Public Stake
    pshare = li.get_text()
    stk['bscs']['pub_stake'] = p2f(pshare.lstrip())

    divTag = divTag.find_next("div", {"class": "com-mid-share-table-wrap", "align": "right"})
    divTag2 = divTag
    for i in range(3):
        divTag2 = divTag2.find_next("div")

    li = divTag2.ul.li
    # FII Stake
    #pshare = divTag2.ul.li.get_text()
    pshare = li.get_text()
    stk['bscs']['fii_stake'] = p2f(pshare.lstrip())
    li = li.find_next("li")
    # DII Stake
    #pshare = divTag2.ul.li.find_next_sibling("li").get_text()
    pshare = li.get_text()
    stk['bscs']['dii_stake'] = p2f(pshare.lstrip())
    li = li.find_next("li")
    #Others Stake
    #pshare = divTag2.ul.li.find_next_sibling("li").find_next_sibling("li").get_text()
    pshare = li.get_text()
    stk['bscs']['others_stake'] = p2f(pshare.lstrip())



############# BASICS ##################


############# FIGURES ##################
    #Get Annual Results.
    #Prefer consolidated.

    annual = soup.find("section", {"id":"Annual"})
    if not annual:
        PRINT_ERR("Unable to parse Annual Statements")
        print(soup)
        return None
    annual_cons = annual.find("table", {"id": "tblAnnualCons", "class": "table table-bordered table-striped"})
    if annual_cons:
        if annual_cons.has_attr("style") and str(annual_cons['style']) == 'display: none;':
            annual_cons = annual.find("table", {"id": "tblAnnualStd", "class": "table table-bordered table-striped"})
            if not annual_cons:
                PRINT_DBG("No Standalone results. Checking Annual")
                annual_cons = annual.find("table", {"id": "tblAnnual", "class": "table table-bordered table-striped"})
                if not annual_cons:
                    PRINT_ERR("Unable to find annual results, skipping this stock")
                    return None
    else:
        PRINT_DBG("No Consolidated results. Checking for standalone results")
        annual_cons = annual.find("table", {"id": "tblAnnualStd", "class": "table table-bordered table-striped"})
        if not annual_cons:
            PRINT_DBG("No Standalone results. Checking Annual")
            annual_cons = annual.find("table", {"id": "tblAnnual", "class": "table table-bordered table-striped"})
            if not annual_cons:
                PRINT_ERR("Unable to find annual results, skipping this stock")
                return None

    PRINT_DBG(annual_cons)
    #Years
    PRINT_DBG("Years: %r" %(Years))
    pattern = re.compile(r'Description\n')
    populate_India_item(stk, pattern, annual_cons, Years, 0)
    PRINT_DBG(stk['fig']['entries'][Years])
    #Sales
    PRINT("Sales: %r"%(Sales))
    pattern = re.compile(r'Net Sales')
    if populate_India_item(stk, pattern, annual_cons, Sales, 1) is False:
        pattern = re.compile(r'Net Interest Income')
        div = annual_cons.find(text=pattern)
        PRINT_DBG(div.parent.parent)
        if div is None:
            PRINT_ERR("Unable to get Net Interest Income")
            return None
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, Sales, 1)
        #populate_India_item(stk, pattern, annual_cons, Sales, 1)
    #Profit Before Taxes
    PRINT_DBG("PBT: %r" %(PBT))
    pattern = re.compile(r'PBT\n')
    populate_India_item(stk, pattern, annual_cons, PBT, 1)
    #Tax
    PRINT_DBG("Taxes: %r" %(Taxes))
    pattern = re.compile(r'Tax\n')
    populate_India_item(stk, pattern, annual_cons, Taxes, 1)

    PRINT_DBG("PAT: %r" %(PAT))
    calculate_PAT(stk)

    #PAT Margin
    pattern = re.compile(r'PAT Margin\n')
    populate_India_item(stk, pattern, annual_cons, PAT_M, 1)
 
    #EPS
    PRINT_DBG("EPS: %r, indices: %r" %(EPS, indices))
    pattern = re.compile(r'Unadjusted EPS\n')
    populate_India_item(stk, pattern, annual_cons, EPS, 1)

    try:
        stk['fig']['ttm_eps'] = stk['fig']['entries'][EPS][-1]
        PRINT("TTM EPS: %r" %(stk['fig']['ttm_eps']))
    except IndexError:
        PRINT_DBG("")

#    if stk['fig']['ttm_eps'] <= 0:
#        PRINT_ERR("Negative EPS")
#        return None

    # Retrieve Operating Cash Flow
    PRINT_DBG("Cash Flow")
    cash = soup.find("section", {"id":"Cash"})
    if not cash:
        PRINT_ERR("Unable to retrieve CASH FLOW")
        print(soup)
        return None
    cash_flow = cash.find("table", {"id": "tbl_CashFlowCons"})
    if cash_flow:
        if cash_flow.has_attr("style") and str(cash_flow['style']) == 'display: none;':
            cash_flow = cash.find("table", {"id": "tbl_CashFlowStd"})
            if not cash_flow:
                cash_flow = cash.find("table", {"id": "Cash"})
                if not cash_flow:
                    PRINT_ERR("Unable to find cash flow info, skipping stock")
                    return None
    else:
        cash_flow = cash.find("table", {"id": "tbl_CashFlowStd"})
        if not cash_flow:
            cash_flow = cash.find("table", {"id": "Cash"})
            if not cash_flow:
                PRINT_ERR("Unable to find cash flow info, skipping stock")
                return None

    pattern = re.compile(r'Cash From Operating Activity')
    div = cash_flow.find(text=pattern)
    div = div.parent.parent
    div = div.find_next("div", {"class": "CHead"})
    populate_India_entry(stk, div, CASH, 1)

    fin_ratios = soup.find("section", {"id": "Financial"})
    #f = open("man_fin_ratios.html", "w")
    #f.write(fin_ratios.prettify())
    #f.close()
    fin = fin_ratios.find("div", {"id": "DivFinancialRatios_Cons"})
    if fin:
        PRINT_DBG(fin)
        if fin.has_attr("style") and str(fin['style']) == 'display: none;':
            PRINT("Fin Ratios Display None")
            fin = fin_ratios.find("div", {"id": "DivFinancialRatios_Std"})
            if not fin:
                PRINT("Unable to find Financial Ratios, skipping stock")
                return None
    else:
        fin = fin_ratios.find("div", {"id": "DivFinancialRatios_Std"})
        if not fin:
            PRINT_ERR("Unable to find Financial Ratios, skipping stock")
            return None

    #label: BOOK
    # Retrieve Book Value
    PRINT_DBG("Book Value")
    pattern = re.compile(r'Book Value')
    div = fin.find(text=pattern)
    if not div:
        PRINT_ERR("Unable to get Book Value")
        print(fin)
        exit()
        #populate_dummy(stk, BOOK)
    else:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, BOOK, 1)

    # Retrieve ROA
    PRINT_DBG("ROA")
    pattern = re.compile(r'ROA')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, ROA, 1)

    # Retrieve ROE
    PRINT_DBG("ROE")
    pattern = re.compile(r'ROE')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, ROE, 1)

    # Retrieve ROCE
    PRINT_DBG("ROCE")
    pattern = re.compile(r'ROCE')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, ROCE, 1)

    # Retrieve Total Debt/Equity
    PRINT_DBG("Total Debt/Equity")
    pattern = re.compile(r'Total Debt/Equity')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, DtoE, 1)

    # Retrieve Total Debt/Equity
    PRINT_DBG("Interest Coverage")
    pattern = re.compile(r'Interest Cover')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate_India_entry(stk, div, INTR, 1)

############# FIGURES ##################
    return stk

# Get stock information of "stock_name"
def get_India_stock_info(stock_page):
    try:
        html = open(stock_page)
    except FileNotFoundError:
        PRINT_ERR("Failed to open %s" %(stock_page))
        return None
    stk = populate_India_stock(html)
    html.close()
    return stk

def populate_US_stocks_quarterly(root, files, stk):
    #stk = Stock()
    shares = []
    liabilities = []
    debt = []
    equity = []
    assets = []
    book = []
    dtoe = []
    roe  = []
    roa  = []
    roce = []
    intr = []

    cash = []
    ppe  = []
    depreciation = []
    capex = []

    quarters = []
    sales = []
    income_tax = []
    pbt = []
    pat = []
    pat_m = []
    basic_eps = []
    basic_cont_eps = []
    diluted_eps = []
    diluted_cont_eps = []

    if len(files) == 0:
        PRINT_ERR("len(files): %d" %(len(files)))
        write_to_unparsed(root)
        write_to_unparsed("len(files): 0")
        return False

    for f in [s for s in files if 'balance_sheet_quarterly' in s]:
        #balance sheets
        stock_page = "%s/%s" %(root, f)
        html_page  = internet.get_html(stock_page)
        soup=BeautifulSoup(html_page,'html.parser')
        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
        div = soup.find(text=pattern)
        if div:
            PRINT_ERR("%s has no data in %s" %(stk['bscs']['symbol'], f))
            continue
        try:
            y = soup.find("tr", {"class":"bc-financial-report__row-dates"})
            if not y and len(years) == 0:
                PRINT_ERR("Unable to get quarterly financial reports")
                return False

            l=y.find_all("td")
            for i in range(1, len(l)):
                quarters.append(str(l[i].get_text().lstrip().rstrip()))
        except AttributeError:
            PRINT_ERR("Unable to get quarterly financial reports")
            return False

        entries = get_entries(soup, re.compile('^ Shares Outstanding, K $'))
        if(len(entries) > 0):
            shares.extend(entries)
        else:
            shares.extend(get_entries(soup, re.compile('^ Common Shares $')))
            stk['fig']['common_shares'] = 1
        liabilities.extend(get_entries(soup, 'Total liabilities'))
        assets.extend(get_entries(soup, 'Total Liabilities And Equity'))
        #debt.extend(get_debt(soup, 'TOTAL'))
    
    if(len(shares) == 0):
        PRINT_ERR("Shares data not found, still continuing")
        write_to_unparsed(stk['bscs']['name'])
        write_to_unparsed("Shares data not found")
        ##return False

    for i in range(lowest_3(len(assets), len(liabilities), len(shares))):
        equity.append(round(assets[i] - liabilities[i],2))
        try:
            if(len(shares) != 0):
                book.append(round((assets[i] - liabilities[i]) / shares[i],2))
            else:
                book.append(0)
        except ZeroDivisionError:
            book.append(0)
        except IndexError:
            print(len(shares))
            print(len(assets))
            print(len(liabilities))
            exit()
    
    if(len(book) == 0):
        err = "len(assets): %d, len(liabilities): %d , len(book): %d data not found"%(len(assets), len(liabilities), len(book))
        PRINT_ERR(err)
        write_to_unparsed(stk['bscs']['name'])
        write_to_unparsed(err)
        ##return False

    for i in range(lowest(len(liabilities), len(equity))):
    #for i in range(lowest(len(debt), len(equity))):
        try:
            dtoe.append(round((liabilities[i]/equity[i]),2))
            #dtoe.append(round((debt[i]/equity[i]),2))
        except ZeroDivisionError:
            dtoe.append(0)

    for f in [s for s in files if 'cash_flow_quarterly' in s]:
        #cash flow statements
        stock_page = "%s/%s" %(root, f)
        html_page  = internet.get_html(stock_page)
        soup=BeautifulSoup(html_page,'html.parser')
        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
        div = soup.find(text=pattern)
        if div:
            PRINT_ERR("%s has no data in %s" %(stk['bscs']['symbol'], f))
            continue
 
        depreciation.extend(get_entries(soup, re.compile('^ Depreciation Amortization $')))
        ppe.extend(get_entries(soup, re.compile('^ PPE Investments $')))
        cash.extend(get_entries(soup, 'Operating Cash Flow'))

    for i in range(lowest(len(depreciation), len(ppe))):
        ppe[i] = abs(ppe[i])
        depreciation[i] = abs(depreciation[i])
        capex.append(round(ppe[i] + depreciation[i],2))

    for f in [s for s in files if 'income_quarterly' in s]:
        #income statements
        stock_page = "%s/%s" %(root, f)
        html_page  = internet.get_html(stock_page)
        soup=BeautifulSoup(html_page,'html.parser')
        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
        div = soup.find(text=pattern)
        if div:
            PRINT_ERR("%s has no data in %s" %(stk['bscs']['symbol'], f))
            continue
 
        #print(soup.prettify())
        sales.extend(get_entries(soup, re.compile('^ Sales $')))
        pbt.extend(get_entries(soup, re.compile('^ Pre-tax Income $')))
        pat.extend(get_entries(soup, 'Net Income $M'))
        income_tax.extend(get_entries(soup, re.compile('^ Income Tax $')))
        basic_eps.extend(get_entries(soup, re.compile('^ EPS Basic Total Ops $')))
        basic_cont_eps.extend(get_entries(soup, re.compile('^ EPS Basic Continuous Ops $')))
        diluted_eps.extend(get_entries(soup, re.compile('^ EPS Diluted Total Ops $')))
        diluted_cont_eps.extend(get_entries(soup, re.compile('^ EPS Diluted Continuous Ops $')))

    #if len(sales) == 0 or len(pat) == 0 or len(eps) == 0:
    #    err= "len(sales): %d, len(pat): %d len(eps): %d data not found"%(len(sales), len(pat), len(eps))
    #    write_to_unparsed(stk['bscs']['name'])
    #    write_to_unparsed(err)
    #    return False

    for i in range(lowest(len(pat), len(equity))):
        try:
            roe.append(round((pat[i]/equity[i]),2))
        except ZeroDivisionError:
            roe.append(0)
    for i in range(lowest(len(pat), len(assets))):
        try:
            roa.append(round((pat[i]/assets[i]),2))
        except ZeroDivisionError:
            roa.append(0)
    for i in range(lowest(len(sales), len(pat))):
        try:
            pat_m.append(round((pat[i]/sales[i])*100 ,2))
        except ZeroDivisionError:
            pat_m.append(0)
    for i in range(lowest(len(capex), len(pat))):
        try:
            roce.append(round(pat[i] / capex[i],2))
            #roce.append(round(ebit[i] / capex[i],2))
        except ZeroDivisionError:
            roce.append(0)

    if len(diluted_cont_eps) > 0:
        stk['fig']['ttm_eps'] = diluted_cont_eps[0]
    else:
        stk['fig']['ttm_eps'] = 0

    stk['quart_fig']['Quarters'].extend(reversed(quarters))
    stk['quart_fig']['Sales'].extend(reversed(sales))
    stk['quart_fig']['PBT'].extend(reversed(pbt))
    stk['quart_fig']['PAT'].extend(reversed(pat))
    stk['quart_fig']['Taxes'].extend(reversed(income_tax))
    stk['quart_fig']['PAT_M'].extend(reversed(pat_m))
    stk['quart_fig']['BASIC_EPS'].extend(reversed(basic_eps))
    stk['quart_fig']['BASIC_CONT_EPS'].extend(reversed(basic_cont_eps))
    stk['quart_fig']['DILUTED_EPS'].extend(reversed(diluted_eps))
    stk['quart_fig']['DILUTED_CONT_EPS'].extend(reversed(diluted_cont_eps))

    stk['quart_fig']['BOOK'].extend(reversed(book))
    stk['quart_fig']['LIABILITIES'].extend(reversed(liabilities))
    #stk['fig']['DEBT'].extend(reversed(debt))
    stk['quart_fig']['ASSETS'].extend(reversed(assets))
    stk['quart_fig']['EQUITY'].extend(reversed(equity))
    stk['quart_fig']['SHARES'].extend(reversed(shares))

    stk['quart_fig']['CASH'].extend(reversed(cash))
    stk['quart_fig']['PPE'].extend(reversed(ppe))
    stk['quart_fig']['DEPRECIATION'].extend(reversed(depreciation))
    stk['quart_fig']['CAPEX'].extend(reversed(capex))
    
    stk['quart_fig']['ROA'].extend(reversed(roa))
    stk['quart_fig']['ROE'].extend(reversed(roe))
    stk['quart_fig']['ROCE'].extend(reversed(roce))
    stk['quart_fig']['DtoE'].extend(reversed(dtoe))
    stk['quart_fig']['INTR'].extend(reversed(intr))

    return stk

# Get last date of financial statements
def get_last_date(stk, fig, statement):
    dates = list(stk[fig]['financial-statements'][statement].keys())

    if 'date' in dates:
        i = dates.index('date')
        del dates[i]

    dt_dates=[]
    for d in dates:
        d = dt.strptime(d, "%m-%Y").date()
        dt_dates.append(d)
    dt_dates = sorted(dt_dates)
    if len(dt_dates) > 0:
        return dt_dates[-1]
    return dt.strptime("01-1950", "%m-%Y").date()

def populate_statement(soup, stock, statement, tenure):
    dates = []

    trs = soup.findAll("tr")
    if len(trs) < 1:
        return
    i=0
    j=0
    if tenure == 'annual':
        fig = 'fig'
    else:
        fig = 'quart_fig'

    if fig not in stock:
        stock[fig]={}
    if 'financial-statements' not in stock[fig].keys():
        stock[fig]['financial-statements']={}
    if statement not in stock[fig]['financial-statements'].keys():
        stock[fig]['financial-statements'][statement]={}

    last_date = get_last_date(stock, fig, statement)
    count = len(trs)
    # Dates
    if trs[i].attrs['class'] and trs[i].attrs['class'][0] == 'bc-financial-report__row-dates':
        tds = trs[i].findAll('td')

        for j in range(1, len(tds)):
            #dates.append(tds[j].get_text().lstrip().rstrip())
            d = datetime.strptime(tds[j].get_text().lstrip().rstrip(), "%m-%Y").date()
            if d > last_date:
                dates.append(datetime.strptime(tds[j].get_text().lstrip().rstrip(), "%m-%Y").date())
            else:
                dates.append("")
        i = i + 1
        # Create statement entry for each date
        for j in range(len(dates)):
            if dates[j] != "":
                stock[fig]['financial-statements'][statement][dates[j]]={}
   
    if len(dates) == 0:
        PRINT_ERR("Couldn't get dates. Unable to proceed")
        sys.exit(1)

    while i < count:
        # Groups of Information like Assets, Liabilities etc

        # income-statement does not have a group label. eg 'Assets' for balance sheet
        if statement != 'income-statement':
            group_label = trs[i].get_text().lstrip().rstrip()
            # Create group label entry for each date
            for j in range(len(dates)):
                if dates[j] != "" and not group_label in stock[fig]['financial-statements'][statement][dates[j]]:
                    stock[fig]['financial-statements'][statement][dates[j]][group_label] = {}
            i = i + 1
        while i < count:
            try:
                if trs[i].attrs['class'] and trs[i].attrs['class'][0] == 'bc-financial-report__row-group-label':
                        break
            except Exception as e:
                print(str(e))
                print(stock[fig]['financial-statements'][statement])
                sys.exit(1)

            tds = trs[i].findAll('td')
            sub_label = tds[0].get_text().lstrip().rstrip()

            if statement == 'income-statement':
                for j, k in zip(range(len(dates)), range(1, len(tds))):
                    if dates[j] != "":
                        stock[fig]['financial-statements'][statement][dates[j]][sub_label] = str_to_float(tds[k].get_text())
            else:
                for j, k in zip(range(len(dates)), range(1, len(tds))):
                    if dates[j] != "":
                        stock[fig]['financial-statements'][statement][dates[j]][group_label][sub_label]=str_to_float(tds[k].get_text())
                        #stock['fig'][statement][dates[j]][group_label].insert(-1, sub_label = str_to_float(tds[k].get_text()))

            i = i + 1
    print(dates)
    return stock

def populate_financial_statement(stock, root, files, sheet_type, tenure):
    substr="%s_%s" %(sheet_type, tenure) #balance-sheet_annual

    if tenure == 'annual':
        fig = 'fig'
    else:
        fig = 'quart_fig'

    for f in [s for s in files if substr in s]:
        #balance sheets
        stock_page = "%s/%s" %(root, f)
        print(stock_page)
        html_page  = internet.get_html(stock_page)
        soup=BeautifulSoup(html_page,'html.parser')
        stock = populate_statement(soup, stock, sheet_type, tenure)

    #Some time quarterly or annual balance or other sheets data is not available.
    #Handle it
    if sheet_type not in stock[fig]['financial-statements'].keys():
        return stock

    sorted_entries = {}
    # Sort entries based on date
    for e in sorted(stock[fig]['financial-statements'][sheet_type].keys()):
        #sorted_entries[e] = stock[fig]['financial-statements'][sheet_type][e]
        sorted_entries[e.strftime('%m-%Y')] = stock[fig]['financial-statements'][sheet_type][e]

    stock[fig]['financial-statements'][sheet_type] = sorted_entries
    return stock

def populate_US_stocks(db, root, files, stock, symbol, name, sector, industry):

    if len(files) == 0:
        PRINT_ERR("len(files): %d" %(len(files)))
        count = db.US_Stocks.find({'bscs.symbol':symbol})
        if count == 0:
            stock['bscs']={}
            stock['bscs']['symbol'] = symbol
            stock['bscs']['name'] = name
            stock['fig']={}
            stock['fig']['financial-statements'] = {}
            stock['quart_fig']['financial-statements'] = {}
            DB.write_to_collection(db['US_Stocks'], stock)
        else:
            DB.update_field(db['US_Stocks'], symbol, "fig.financial-statements", {})
            DB.update_field(db['US_Stocks'], symbol, "quart_fig.financial-statements", {})
        return False

    #Name and Symbol
    if 'bscs' not in stock.keys():
        stock['bscs']={}
    if 'fig' not in stock.keys():
        stock['fig']={}
    if 'quart_fig' not in stock.keys():
        stock['quart_fig']={}

    stock['bscs']['symbol'] = symbol
    stock['bscs']['name'] = name
    stock['bscs']['sector'] = sector
    stock['bscs']['industry'] = industry
    stock['fig']['financial-statements']={}
    stock['quart_fig']['financial-statements']={}

    stock = populate_financial_statement(stock, root, files, 'balance-sheet', 'annual')
    stock = populate_financial_statement(stock, root, files, 'balance-sheet', 'quarterly')
    stock = populate_financial_statement(stock, root, files, 'cash-flow', 'annual')
    stock = populate_financial_statement(stock, root, files, 'cash-flow', 'quarterly')
    stock = populate_financial_statement(stock, root, files, 'income-statement', 'annual')
    stock = populate_financial_statement(stock, root, files, 'income-statement', 'quarterly')

    #pretty_print(stock)
    DB.write_to_collection(db['US_Stocks'], stock)

    #DB.update_field(db['US_Stocks'], stock['bscs']['symbol'], "fig", stock['fig']['financial-statements'])
    #DB.update_field(db['US_Stocks'], stock['bscs']['symbol'], "fig.financial-statements", stock['fig']['financial-statements'])
    #DB.update_field(db['US_Stocks'], stock['bscs']['symbol'], "quart_fig.financial-statements", stock['quart_fig']['financial-statements'])
    url = 'https://www.barchart.com/stocks/quotes/%s/profile' %(symbol)
    html_page=internet.get_webpage(url)
    DB.update_US_stk_profile(html_page, db.US_Stocks)

    return True


#def populate_US_stocks(db, root, files, symbol, name, sector, industry):
#    stk = Stock()
#    #db = DB.open_db('Stocks')
#    #stk = db.US_Stocks.find({"bscs.symbol":"BORR"}).next()
#    #del stk['_id']
#    #stk = DB.clear_dict(stk)
#    stk = json_code.build_json_object(stk)
#    stk['ignore'] = 'No'
#    shares = []
#    liabilities = []
#    debt = []
#    equity = []
#    assets = []
#    book = []
#    dtoe = []
#    roe  = []
#    roa  = []
#    roce = []
#    intr = []
#
#    cash = []
#    ppe  = []
#    depreciation = []
#    capex = []
#
#    years = []
#    sales = []
#    income_tax = []
#    pbt = []
#    pat = []
#    pat_m = []
#    eps = []
#
#    #print(years)
#    #print(files)
#    #Years
#    #root = 'US_Stocks/html_pages/Silvercorp Metals Inc.'
#    #files = ['SVM_balance_sheet_1.html', 'SVM_balance_sheet_2.html', 'SVM_cash_flow_1.html', 'SVM_cashflow_2.html', 'SVM_income_1.html', 'SVM_income_2.html']
#
#    #root = 'US_Stocks/html_pages/Nordic American Offshore Ltd.'
#    #files = ['NAO_balance_sheet_1.html', 'NAO_balance_sheet_2.html', 'NAO_cash_flow_1.html', 'NAO_cashflow_2.html', 'NAO_income_1.html', 'NAO_income_2.html']
#
#    if len(files) == 0:
#        PRINT_ERR("len(files): %d" %(len(files)))
#        write_to_unparsed(root)
#        write_to_unparsed("len(files): 0")
#        return False
#
#    #stock_page = "%s/%s" %(root, files[0])
#    #html_page  = internet.get_html(stock_page)
#    #soup=BeautifulSoup(html_page,'html.parser')
#    ##print(soup.prettify())
#    #try:
#    #    y = soup.find("tr", {"class":"bc-financial-report__row-dates"})
#    #    l=y.find_all("td")
#    #    for i in range(1, len(l)):
#    #        years.extend(str(l[i]).lstrip().rstrip())
#    #except AttributeError:
#    #    PRINT_ERR("Unable to get financial reports")
#    #    return False
#
#    #stock_page = "%s/%s" %(root, files[1])
#    ##print(stock_page)
#    #html_page  = internet.get_html(stock_page)
#    #soup=BeautifulSoup(html_page,'html.parser')
#    #try:
#    #    y = soup.find("tr", {"class":"bc-financial-report__row-dates"})
#    #    l=y.find_all("td")
#    #    for i in range(1, len(l)):
#    #        years.extend(str(l[i]).lstrip().strip())
#    #    count = 2
#    #except AttributeError:
#    #    count = 1
#
#    #Name and Symbol
#    stk['bscs']['symbol'] = symbol
#    stk['bscs']['name'] = name
#    stk['bscs']['sector'] = sector
#    stk['bscs']['industry'] = industry
#    #s = soup.find("div", {"class": "symbol-name"})
#    #print(s)
#    #stk['bscs']['symbol'] = s.find_next("span").find_next("span").get_text().replace("(","").replace(")","")
#    #stk['bscs']['name']   = yf(stk['bscs']['symbol']).get_stock_quote_type_data()[stk['bscs']['symbol']]['shortName'] 
#    #stk['bscs']['name']   = s.find_next("span").get_text()
#   
#
##    for f in [s for s in files if 'profile' in s]:
##        stock_page = "%s/%s" %(root, f)
##        html_page  = internet.get_html(stock_page)
##        DB.update_US_stk_profile(html_page, db.US_Stocks)
#
#    for f in [s for s in files if 'balance_sheet_annual' in s]:
#        #balance sheets
#        stock_page = "%s/%s" %(root, f)
#        html_page  = internet.get_html(stock_page)
#        soup=BeautifulSoup(html_page,'html.parser')
#
#        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
#        div = soup.find(text=pattern)
#        if div:
#            PRINT_ERR("%s has no data in %s" %(stk['bscs']['symbol'], f))
#            continue
# 
#        try:
#            y = soup.find("tr", {"class":"bc-financial-report__row-dates"})
#            if not y and len(years) == 0:
#                PRINT_ERR("%s: %s: Unable to get annual balance sheet data" %(stk['bscs']['symbol'], stk['bscs']['name']))
#                return False
#
#            l=y.find_all("td")
#            for i in range(1, len(l)):
#                years.append(str(l[i].get_text().lstrip().rstrip()))
#        except AttributeError:
#            PRINT_ERR("Attr Err: Unable to get annual balance sheets")
#            return False
#
#        shares.extend(get_entries(soup, re.compile('^ Shares Outstanding, K $')))
#        if(len(shares) == 0):
#            shares.extend(get_entries(soup, re.compile('^ Common Shares $')))
#            stk['fig']['common_shares'] = 1
#        liabilities.extend(get_entries(soup, 'Total liabilities'))
#        assets.extend(get_entries(soup, 'Total Liabilities And Equity'))
#        #debt.extend(get_debt(soup, 'TOTAL'))
#    
#    if(len(shares) == 0):
#        PRINT_ERR("Shares data not found, still continuing")
#        write_to_unparsed(stk['bscs']['name'])
#        write_to_unparsed("Shares data not found")
#        ##return False
#
##    stk['bscs']['price']  = yf(stk['bscs']['symbol']).get_current_price()
##    stk['bscs']['volume'] = yf(stk['bscs']['symbol']).get_current_volume()
##    stk['bscs']['mcap']   = yf(stk['bscs']['symbol']).get_market_cap()/1000000
#
#
#    for i in range(lowest_3(len(assets), len(liabilities), len(shares))):
#        equity.append(round(assets[i] - liabilities[i],2))
#        try:
#            if(len(shares) != 0):
#                book.append(round((assets[i] - liabilities[i]) / shares[i],2))
#            else:
#                book.append(0)
#        except ZeroDivisionError:
#            book.append(0)
#        except IndexError:
#            print(len(shares))
#            print(len(assets))
#            print(len(liabilities))
#            exit()
#    
#    if(len(book) == 0):
#        err = "len(assets): %d, len(liabilities): %d , len(book): %d data not found, still continuing"%(len(assets), len(liabilities), len(book))
#        PRINT_ERR(err)
#        write_to_unparsed(stk['bscs']['name'])
#        write_to_unparsed(err)
#        ##return False
#
#    for i in range(lowest(len(liabilities), len(equity))):
#    #for i in range(lowest(len(debt), len(equity))):
#        try:
#            dtoe.append(round((liabilities[i]/equity[i]),2))
#            #dtoe.append(round((debt[i]/equity[i]),2))
#        except ZeroDivisionError:
#            dtoe.append(0)
#
#    for f in [s for s in files if 'cash_flow_annual' in s]:
#        #cash flow statements
#        stock_page = "%s/%s" %(root, f)
#        html_page  = internet.get_html(stock_page)
#        soup=BeautifulSoup(html_page,'html.parser')
#
#        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
#        div = soup.find(text=pattern)
#        if div:
#            PRINT_ERR("%s has no data in %s" %(stk['bscs']['symbol'], f))
#            continue
# 
#        depreciation.extend(get_entries(soup, re.compile('^ Depreciation Amortization $')))
#        ppe.extend(get_entries(soup, re.compile('^ PPE Investments $')))
#        cash.extend(get_entries(soup, 'Operating Cash Flow'))
#
#    for i in range(lowest(len(depreciation), len(ppe))):
#        ppe[i] = abs(ppe[i])
#        depreciation[i] = abs(depreciation[i])
#        capex.append(round(ppe[i] + depreciation[i],2))
#
#    for f in [s for s in files if 'income_annual' in s]:
#        #income statements
#        stock_page = "%s/%s" %(root, f)
#        html_page  = internet.get_html(stock_page)
#        soup=BeautifulSoup(html_page,'html.parser')
#
#        pattern = re.compile(r'Sorry, there is no additional data for this symbol.')
#        div = soup.find(text=pattern)
#        if div:
#            PRINT_ERR("%s has no data in %s" %(stk['bscs']['symbol'], f))
#            continue
# 
#        #print(soup.prettify())
#        sales.extend(get_entries(soup, re.compile('^ Sales $')))
#        pbt.extend(get_entries(soup, re.compile('^ Pre-tax Income $')))
#        pat.extend(get_entries(soup, 'Net Income $M'))
#        income_tax.extend(get_entries(soup, re.compile('^ Income Tax $')))
#        eps.extend(get_entries(soup, re.compile('^ EPS Diluted Continuous Ops $')))
#
#    #if len(sales) == 0 or len(pat) == 0 or len(eps) == 0:
#    #    err= "len(sales): %d, len(pat): %d len(eps): %d data not found"%(len(sales), len(pat), len(eps))
#    #    write_to_unparsed(stk['bscs']['name'])
#    #    write_to_unparsed(err)
#    #    return False
#
#    for i in range(lowest(len(pat), len(equity))):
#        try:
#            roe.append(round((pat[i]/equity[i]),2))
#        except ZeroDivisionError:
#            roe.append(0)
#    for i in range(lowest(len(pat), len(assets))):
#        try:
#            roa.append(round((pat[i]/assets[i]),2))
#        except ZeroDivisionError:
#            roa.append(0)
#    for i in range(lowest(len(sales), len(pat))):
#        try:
#            pat_m.append(round((pat[i]/sales[i])*100 ,2))
#        except ZeroDivisionError:
#            pat_m.append(0)
#    for i in range(lowest(len(capex), len(pat))):
#        try:
#            roce.append(round(pat[i] / capex[i],2))
#            #roce.append(round(ebit[i] / capex[i],2))
#        except ZeroDivisionError:
#            roce.append(0)
#
#    if len(eps) > 0:
#        stk['fig']['ttm_eps'] = eps[0]
#    else:
#        stk['fig']['ttm_eps'] = 0
#
#    stk['fig']['Years'].extend(reversed(years))
#    stk['fig']['Sales'].extend(reversed(sales))
#    stk['fig']['PBT'].extend(reversed(pbt))
#    stk['fig']['PAT'].extend(reversed(pat))
#    stk['fig']['Taxes'].extend(reversed(income_tax))
#    stk['fig']['PAT_M'].extend(reversed(pat_m))
#    stk['fig']['EPS'].extend(reversed(eps))
#
#    stk['fig']['BOOK'].extend(reversed(book))
#    stk['fig']['LIABILITIES'].extend(reversed(liabilities))
#    #stk['fig']['DEBT'].extend(reversed(debt))
#    stk['fig']['ASSETS'].extend(reversed(assets))
#    stk['fig']['EQUITY'].extend(reversed(equity))
#    stk['fig']['SHARES'].extend(reversed(shares))
#
#    stk['fig']['CASH'].extend(reversed(cash))
#    stk['fig']['PPE'].extend(reversed(ppe))
#    stk['fig']['DEPRECIATION'].extend(reversed(depreciation))
#    stk['fig']['CAPEX'].extend(reversed(capex))
#    
#    stk['fig']['ROA'].extend(reversed(roa))
#    stk['fig']['ROE'].extend(reversed(roe))
#    stk['fig']['ROCE'].extend(reversed(roce))
#    stk['fig']['DtoE'].extend(reversed(dtoe))
#    stk['fig']['INTR'].extend(reversed(intr))
#
#    #stk = get_price_volume(stk, 'US')
#
#    DB.build_US_quarterly_stock_information(stk)
#
#    #obj = json_code.build_json_object(stk)
#    #if obj:
#    #    DB.write_to_collection(db['US_Stocks'], obj)
#    #    del obj
#    #    obj = None
#    DB.write_to_collection(db['US_Stocks'], stk)
# 
#    del stk
#    stk = None
#
#    print("Profile Information")
#    for f in [s for s in files if 'profile' in s]:
#        stock_page = "%s/%s" %(root, f)
#        html_page  = internet.get_html(stock_page)
#        DB.update_US_stk_profile(html_page, db.US_Stocks)
#
#    return True

    
