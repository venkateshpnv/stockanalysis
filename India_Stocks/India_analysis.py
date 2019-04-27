import conf

import time
#Web Driver
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import TimeoutException

# Parsing HTML
import requests 
from bs4 import BeautifulSoup 

#Yahoo Financials
from yahoofinancials import YahooFinancials as yf

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
from fractions import Fraction
#Print Line number
from inspect import currentframe
import datetime
import json
import pprint
import pymongo

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
PAT_M = indices
indices+=1
#Unadjusted EPS
EPS = indices
indices+=1
CASH = indices
indices+=1
BOOK = indices
indices+=1
ROA = indices
indices+=1
ROE = indices
indices+=1
ROCE = indices
indices+=1
DtoE = indices
indices+=1
#Interest Coverage
INTR = indices
indices+=1

#Rupee ASCII in excel
RUPEE = u"\u20B9"

#List of BSE Stocks
bse_stocks="BSE_Stocks.xls"
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
        self.bse_symbol = 'DEAD'
        self.sector = 'DEAD'
        self.price  = 0
        self.promoter_stake = 0
        self.corp_stake     = 0
        self.pub_stake      = 0
        self.fii_stake      = 0
        self.dii_stake      = 0
        self.others_stake   = 0
        self.face_value     = 0
        self.volume         = 0
        self.mcap           = 0
        self.split_date     = 0
        self.split_year     = 0
        self.split_factor   = 1

class Ratios:
    def __init(self):
        self.book_value = 0
        # Percentages
        self.conf.ROA = 0
        self.conf.ROE = 0
        self.conf.ROCE = 0

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
    #entries = list()
    entries = list()
    # number of years of data we have for each field.
    # ex: 10 years of book value, 8 years of cash flow etc.
    #fig_years = [0] * (indices)
    #fig_years = []

    def __init(self):
        self.ttm_eps = 0
        # Long Term Debt
        #self.lt_debt = 0
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0
        self.growth = 0
        #self.entries = [[0] * MAX_YEARS for i in range(indices)]
        #self.entries = [[0 for i in range(MAX_YEARS)] for j in range(indices)]
        self.entries = [[0 for i in range(1)] for j in range(indices)]
        #self.entries = [0 for i in range(indices)]
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
        self.bscs = Basics()
        self.num  = Numbers()
        self.fig  = Figures()

#Supportive calls
def PRINT_ERR(x):
    print("ERR: %s" %(x))
def PRINT_DBG(x):
    None
    #print(x)
def PRINT(x):
    None
    #print(x)

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
    except TypeError:
        return 0
    return val

def str_to_float_valid(x):
    try:
        val = float(x)
        return True
    except ValueError:
        return False

def get_linenumber():
    cf = currentframe()
    return cf.f_back.f_lineno

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

def add_header(sheet):
    sheet.row(0).height_mismatch = True
    sheet.row(0).height = 3*367
    i=1
    #Company
    sheet.col(i).width = 15*367
    sheet.write(0, i, "Company", style_wrap)
    conf.COMP=i

    i+=1
    #Symbol
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Symbol", style_wrap)
    conf.SYM=i

    i+=1
    #Current Price
    sheet.col(i).width = 6*367
    sheet.write(0, i, "Current Price", style_wrap)
    conf.CUR_PR=i

    i+=1
    #DCF Price
    sheet.col(i).width = 5*367
    sheet.write(0, i, "DCF Price", style_wrap)
    conf.DCF_PR=i

    i+=1
    #MoS @50% Price
    sheet.col(i).width = 5*367
    #mos = "MoS Price @%r" %(stk.num.margin_of_safety)
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

    i+=1
    #Volume
    sheet.col(i).width = 7*367
    sheet.write(0, i, "Volume", style_wrap)
    conf.VOL=i

    i += 1
    #Years of Data
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Years of Data", style_wrap)
    conf.YR_DAT=i

    i+=1
    # 10 yr Sales Growth
    sheet.col(i).width = 5*367
    sheet.write(0, i, "10 yr Sales Gr", style_wrap)
    conf.TEN_SAL=i

    i+=1
    # 10 yr Profit Growth
    sheet.col(i).width = 5*367
    sheet.write(0, i, "10 yr Profit Gr", style_wrap)
    conf.TEN_PR=i

    i+=1
    #10 yr Book Value Growth
    sheet.col(i).width = 5*367
    sheet.write(0, i, "10 yr Book Gr", style_wrap)
    conf.TEN_BK=i

    i+=1
    # 10 yr Cash Growth
    sheet.col(i).width = 5*367
    sheet.write(0, i, "10 yr Cash Gr", style_wrap)
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

    i+=1
    # Face Value
    sheet.col(i).width = 5*367
    sheet.write(0, i, "Face Value", style_wrap)
    conf.FV=i

    i+=1
    # P/E
    sheet.col(i).width = 4*367
    sheet.write(0, i, "P/E", style_wrap)
    conf.PE=i

    i+=1
    # DtoTE
    sheet.col(i).width = 5*367
    sheet.write(0, i, "DtoTE", style_wrap)
    conf.DTOTE=i

    i+=1
    # Interest Coverage
    sheet.col(i).width = 4*367
    sheet.write(0, i, "Intr Covr", style_wrap)
    conf.INT_C=i

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


#com : Company Work Book
#ash : All Stocks Work Sheet
#stk : Stock information
def write_to_excel(com, ash, stk):
    #wb = xlwt.Workbook()

    #open a company sheet
    sheet = com.add_sheet(stk.bscs.symbol)
    sheet.col(0).width = 28*367
    sheet.col(1).width = 10*367
    sheet.col(3).width = 10*367

    i = 0
    sheet.write(i, 0, "Date", style_bold)
    sheet.write(i, 1, arrow.now().format('DD-MM-YYYY'))
    #sheet.write(0, 1, str(date.today()))

    i = 2
    sheet.write(i, 0, "Basics")

    i += 1 #row 4
    sheet.write(i, 0, "Name")
    sheet.write(i, 1, stk.bscs.name)
    ash.write(conf.COUNT, conf.COMP, stk.bscs.name, style_text)

    sheet.write(i, 3, "Promoter Stake")
    sheet.write(i, 4, stk.bscs.promoter_stake/100, style_percent)
    ash.write(conf.COUNT, conf.PRM_S, stk.bscs.promoter_stake/100, style_percent)
    ash.write(conf.COUNT, conf.FII, stk.bscs.fii_stake/100, style_percent)
    ash.write(conf.COUNT, conf.DII, stk.bscs.dii_stake/100, style_percent)

    i += 1 #row 5
    sheet.write(i, 0, "Symbol")
    sheet.write(i, 1, stk.bscs.symbol)
    ash.write(conf.COUNT, conf.SYM, stk.bscs.symbol, style_text)

    sheet.write(i, 3, "Public Stake")
    sheet.write(i, 4, stk.bscs.pub_stake/100, style_percent)

    i += 1 #row 6
    sheet.write(i, 0, "Price")
    sheet.write(i, 1, stk.bscs.price)
    ash.write(conf.COUNT, conf.CUR_PR, stk.bscs.price)

    sheet.write(i, 3, "Volume")
    sheet.write(i, 4, stk.bscs.volume)
    ash.write(conf.COUNT, conf.VOL, stk.bscs.volume)

    i += 1 #row 7
    sheet.write(i, 0, "Face Value")
    sheet.write(i, 1, stk.bscs.face_value)
    ash.write(conf.COUNT, conf.FV, stk.bscs.face_value)

    i += 1 #row 8
    sheet.write(i, 0, "P/E")
    sheet.write(i, 1, round(stk.bscs.price/stk.fig.ttm_eps,2))
    ash.write(conf.COUNT, conf.PE, round(stk.bscs.price/stk.fig.ttm_eps,2))


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
    ash.write(conf.COUNT, conf.YR_DAT, len(stk.fig.entries[SALES]))

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
    yr = "EPS by %r at %r percent inflation" % (now + 5, (stk.num.inflation)*100)
    sheet.write(i, 0, yr)
    sheet.write(i, 1, Formula("$B$31 * ((1-$B$17)^5)"), style_decimal)

    i += 2 #row 36
    sheet.write(i, 0, "Earnings after 20 years")
    sheet.write(i, 1, Formula("SUM($B$25:$K$25) + SUM($B$28:$K$28)"), style_decimal)
    ash.write(conf.COUNT, conf.SAL_PR, round(sum(stk.num.eps_20yr),2), style_decimal)

    i += 1 #row 37
    sheet.write(i, 0, "Today's Value with Inflation")
    sheet.write(i, 1, Formula("$B$35 * ((1-$B$17)^20)"), style_decimal)
    ash.write(conf.COUNT, conf.DCF_PR, stk.num.dcf_price*2, style_decimal)

    i += 1 #row 38
    sheet.write(i, 0, "Price with Margin of Safety")
    sheet.write(i, 1, Formula("$B$36*$B$18"), style_decimal)
    ash.write(conf.COUNT, conf.MOS_PR, stk.num.dcf_price, style_decimal)

    i += 1  # row 39
    sheet.write(i, 0, "Current Price", style_bold)
    sheet.write(i, 1, stk.bscs.price, style_bold)
    sheet.write(i, 2, "Profit", style_bold)

    i += 1 #row 40
    sheet.write(i, 0, "Value of MoS Price after 20 years with inflation")
    sheet.write(i, 1, Formula("$B$37*((1+$B$17)^20)"), style_decimal)
    sheet.write(i, 2, Formula("$B$35-$B$38"), style_decimal)

    i += 1 #row 4
    sheet.write(i, 0, "Rate of return at Current Price")
    sheet.write(i, 1, Formula("($B$35/$B$38)^0.05-1"), style_percent)
    ash.write(conf.COUNT, conf.CUR_RT, stk.num.cp_return_rate, style_percent)
    #sheet.write(i, 1, Formula("((($B$35/$B$39)^(1/$K$27-$B$22))-1)))"), style_percent)

    i += 1 #row 41
    sheet.write(i, 0, "Rate of return at MoS Price")
    sheet.write(i, 1, Formula("($B$35/$B$37)^0.05-1"), style_percent)
    ash.write(conf.COUNT, conf.MOS_RT, stk.num.dcf_return_rate, style_percent)
   
   #Ratios
    ash.write(conf.COUNT, conf.DTOTE, stk.fig.entries[DtoE][-1])
    ash.write(conf.COUNT, conf.INT_C, stk.fig.entries[INTR][-1])
    ash.write(conf.COUNT, conf.ROE, stk.fig.entries[ROE][-1])
    ash.write(conf.COUNT, conf.ROA, stk.fig.entries[ROA][-1])
    ash.write(conf.COUNT, conf.ROCE, stk.fig.entries[ROCE][-1])
    ash.write(conf.COUNT, conf.PRF_M, stk.fig.entries[PAT_M][-1]/100, style_percent)
    ash.write(conf.COUNT, conf.MCAP, stk.bscs.mcap, style_num)
    ash.write(conf.COUNT, conf.TEN_SAL, stk.fig.sales_growth, style_percent)
    ash.write(conf.COUNT, conf.TEN_PR, stk.fig.profit_growth, style_percent)
    ash.write(conf.COUNT, conf.TEN_BK, stk.fig.book_growth, style_percent)
    ash.write(conf.COUNT, conf.TEN_CSH, stk.fig.cash_growth, style_percent)
    #sheet.write(i, 1, Formula("((($B$35/$B$37)^(1/$K$27-$B$22))-1)))"), style_percent)

#    excel = "excel_files/%s.xls" %(stk.bscs.name)

#    PRINT("Writing to %s"%(excel))
#    wb.save(excel)

def get_LTP(sym):
    sym = sym + '.BO'
    return yf(sym).get_current_price()

def build_json_object(stock):
    y=json.dumps(stock, indent=4, default=lambda x:x.__dict__)
    #print(y)
    obj = json.loads(y)
    obj['fig']['Years'] = stock.fig.entries[YEARS]
    obj['fig']['Sales'] = stock.fig.entries[SALES]
    obj['fig']['Profit Before Taxes'] = stock.fig.entries[PBT]
    obj['fig']['Taxes'] = stock.fig.entries[TAX]
    obj['fig']['Profit After Taxes'] = stock.fig.entries[PAT]
    obj['fig']['Profit Margin'] = stock.fig.entries[PAT_M]
    obj['fig']['EPS'] = stock.fig.entries[EPS]
    obj['fig']['Operating Cash Flow'] = stock.fig.entries[CASH]
    obj['fig']['Book Value'] = stock.fig.entries[BOOK]
    obj['fig']['Return on Equity'] = stock.fig.entries[ROE]
    obj['fig']['Return on Assets'] = stock.fig.entries[ROA]
    obj['fig']['Return on Capital Expenditure'] = stock.fig.entries[ROCE]
    obj['fig']['Total Debt to Equity'] = stock.fig.entries[DtoE]
    obj['fig']['Interest Coverage'] = stock.fig.entries[INTR]
    #print(json.dumps(obj, indent=4, default=lambda o:o.__dict__))
#    obj = json.dumps(obj)
#    obj = json.loads(obj)
    return obj
 
def get_stock_page(stock):
    driver = webdriver.Firefox()
    driver.get("http://www.ratestar.in/home")
    old_url = driver.current_url
    elem = driver.find_element_by_name("txtStock")

    elem.clear()
    for i in range(len(stock)):
        elem.send_keys(str(stock[i]))
        time.sleep(10/1000)
        #divs = driver.find_element_by_xpath()
        #s = Select(elem)
        #driver.find_element_by_css_selector("button.btn.btn-default").click()
        opts = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
                (By.ID, 'listPlacementStock')))
        time.sleep(1)
        #soup = BeautifulSoup(driver.page_source, 'html.parser')
        #div = soup.find("div", {"id": "listPlacementStock"})
        ##print(div.prettify())
        #items = div.find_all("div", {"class": "autocomplete_listItem"})
        #print(len(items))
        #print(items)
        PRINT_DBG("Opts: %r : %r" %(len(opts.text), opts.text))

        #if len(items) == 1:
        if len(opts.text) == 0:
            PRINT("Unable to parse %r" % (stock))
            f = open("unparsed_stocks3.txt", "a")
            f.write(stock)
            f.write("\n")
            f.close()
            driver.close()
            return
        if not '\n' in opts.text:
            stock_name = opts.text
            #time.sleep(5)
            elem.send_keys(Keys.RETURN)
            break

        #attr=driver.find_element_by_name('txtStock').get_attribute('innerHTML')
        #attr=elem.get_attribute('innerHTML')
    #elem.send_keys(stock, Keys.ARROW_DOWN)
    #time.sleep(2)
    #elem.send_keys(Keys.RETURN)
    
    #time.sleep(20)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(
        (By.ID, 'lblCompany')))
    except TimeoutException:
        PRINT("Unable to parse %r" %(stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
        return
    #PRINT_DBG(str(html_src))

    if driver.current_url == old_url:
        PRINT("Unable to parse %r" %(stock))
        f = open("unparsed_stocks3.txt", "a")
        f.write(stock)
        f.write("\n")
        f.close()
    else:
        #PRINT_DBG("Found stock %r" %(stock))
        html_src=driver.page_source
        html_file = "html_pages/dir2/%s.html" %(stock_name)
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

# Get stock split information
def get_stock_split_info_yahoo(stk):
    sym = stk.bscs.symbol + '.BO'
    #get split info from Yahoo Finance
    data = yf(sym).get_key_statistics_data()
    stk.bscs.split_factor = float(Fraction(data[sym]['lastSplitFactor']))
    d = data[sym]['lastSplitDate']
    stk.bscs.split_date = d
    stk.bscs.split_year = datetime.datetime.strptime(d, '%Y-%m-%d').year 

def get_stock_split_info(stk):
    wb = xlrd.open_workbook('split_data.xls')
    sheet = wb.sheet_by_index(0)
    for i in range(1,sheet.nrows):
        if str(sheet.cell_value(i, 0)) == stk.bscs.name:
            stk.bscs.split_date = sheet.cell_value(i,1)
            stk.bscs.split_year = datetime.datetime.strptime(stk.bscs.split_date, '%d-%b-%Y').year
            try:
                stk.bscs.split_factor = int(sheet.cell_value(i, 3)) / int(sheet.cell_value(i,4))
            except ZeroDivisionError:
                stk.bscs.split_factor=1
            return
    if stk.bscs.face_value != 10:
        PRINT_ERR("Could not find split date for %s, facevalue: %r" %(stk.bscs.symbol, stk.bscs.face_value))   

# Get symbol name for bse symbol
# Get sector information
def get_symbol_and_sector(stk):
    wb = xlrd.open_workbook(bse_stocks)
    sheet = wb.sheet_by_index(0)
    #sheet.cell_value(0,0)

    for i in range(1,sheet.nrows):
        if str(int(sheet.cell_value(i, 0))) == stk.bscs.bse_symbol:
            stk.bscs.symbol = sheet.cell_value(i,1)
            stk.bscs.sector = sheet.cell_value(i,7)
            return
    PRINT_ERR("Cant find symbol name for %s" %(stk.bscs.bse_symbol))

def populate_item(stk, pattern, section, row, convert):
    div = section.find("div", text=pattern)
    if not div:
        PRINT_ERR("No Match")
        PRINT_ERR(pattern)
        return False
    div = div.parent
    div = div.find_next("div", {"class": "CHead"})
    populate(stk, div, row, convert)
    PRINT_DBG(stk.fig.entries[row])
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
        PRINT_ERR("Unable to get Company name")
        return None
    stk.bscs.name = l.lstrip().rstrip().replace(".","")
    print(stk.bscs.name)

    # Ticker
    l=soup.find(id='lblBSE').get_text()
    #l=soup.find(id='lblNSE').get_text()
    l = l.split(": ", 1)[1]
    stk.bscs.bse_symbol = l
   
    get_symbol_and_sector(stk)

    # Price
    l = get_LTP(stk.bscs.symbol)
    try:
        stk.bscs.price = str_to_float(l)
    except ValueError:
        stk.bscs.price = 0
#    if stk.bscs.price < 1:
#        PRINT_ERR("Price less than 1")
#        return None

    # Face Value
    l=soup.find(id='lblFaceValue').get_text()
    try:
        stk.bscs.face_value = int(l)
    except ValueError:
        stk.bscs.face_value = 10

    get_stock_split_info(stk)

    # Volume
    l=soup.find(id='lblVolume').get_text()
    try:
        stk.bscs.volume = int(l)
    except ValueError:
        stk.bscs.volume = 0

#    if stk.bscs.volume < 50000:
#        return None

    PRINT_DBG("Volume %r" %(stk.bscs.volume))

    #Market Cap
    try:
        l=soup.find(id='lblMCap').get_text()
    except:
        PRINT_ERR("Unable to get market cap")
        return None
    try:
        stk.bscs.mcap = float(l.lstrip().rstrip().replace(",", ""))
    except ValueError:
        stk.bscs.mcap = 0


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
    # conf.FII Stake
    #pshare = divTag2.ul.li.get_text()
    pshare = li.get_text()
    stk.bscs.fii_stake = p2f(pshare.lstrip())
    li = li.find_next("li")
    # conf.DII Stake
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
            PRINT_ERR("Unable to get Net Interest Income")
            return None
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, SALES, 1)
        #populate_item(stk, pattern, annual_cons, SALES, 1)
    #Profit Before Taxes
    PRINT_DBG("PBT: %r" %(PBT))
    pattern = re.compile(r'PBT\n')
    populate_item(stk, pattern, annual_cons, PBT, 1)
    #Tax
    PRINT_DBG("TAX: %r" %(TAX))
    pattern = re.compile(r'Tax\n')
    populate_item(stk, pattern, annual_cons, TAX, 1)

    PRINT_DBG("PAT: %r" %(PAT))
    calculate_PAT(stk)

    #PAT Margin
    pattern = re.compile(r'PAT Margin\n')
    populate_item(stk, pattern, annual_cons, PAT_M, 1)
 
    #EPS
    PRINT_DBG("EPS: %r, indices: %r" %(EPS, indices))
    pattern = re.compile(r'Unadjusted EPS\n')
    populate_item(stk, pattern, annual_cons, EPS, 1)

    try:
        stk.fig.ttm_eps = stk.fig.entries[EPS][-1]
        PRINT("TTM EPS: %r" %(stk.fig.ttm_eps))
    except IndexError:
        PRINT_DBG("")

#    if stk.fig.ttm_eps <= 0:
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
    populate(stk, div, CASH, 1)

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
        populate(stk, div, BOOK, 1)

    # Retrieve ROA
    PRINT_DBG("ROA")
    pattern = re.compile(r'ROA')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, ROA, 1)

    # Retrieve ROE
    PRINT_DBG("ROE")
    pattern = re.compile(r'ROE')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, ROE, 1)

    # Retrieve ROCE
    PRINT_DBG("ROCE")
    pattern = re.compile(r'ROCE')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, ROCE, 1)

    # Retrieve Total Debt/Equity
    PRINT_DBG("Total Debt/Equity")
    pattern = re.compile(r'Total Debt/Equity')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, DtoE, 1)

    # Retrieve Total Debt/Equity
    PRINT_DBG("Interest Coverage")
    pattern = re.compile(r'Interest Cover')
    div = fin.find(text=pattern)
    if div:
        div = div.parent
        div = div.find_next("div", {"class": "CHead"})
        populate(stk, div, INTR, 1)

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
    PRINT("Growth of entries: %r"%(growth))
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
#           val = get_LTP(stock.bscs.symbol)
#           if val == -1:
#               PRINT_ERR("Unable to get LTP for %s"%(stock.bscs.name))
#           else:
#               stock.bscs.price = val

            obj = build_json_object(stock)
            write_to_collection(db['Indian_Stocks'], obj)
            stock = None
            obj   = None

# Get stock information of "stock_name"
def get_stock_info(stock_page):
    try:
        html = open(stock_page)
    except FileNotFoundError:
        PRINT_ERR("Failed to open %s" %(stock_page))
        return None
    stk = populate_stock(html)
    html.close()
    return stk

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
    files = glob.glob("./html_pages/*")
#    files = glob.glob("./html_pages/FILATEX INDIA LTD. .html")
#    files = glob.glob("./html_pages/Krishna Capital and Securities Ltd.html")
#    files = glob.glob("./html_pages/STERLING TOOLS LTD. .html")
#    files = glob.glob("./html_pages/WELSPUN INDIA LTD..html")
#    files = glob.glob("./html_pages/LT FOODS LTD..html")
#    files = glob.glob("./html_pages/PIDILITE INDUSTRIES LTD..html")
#    files = glob.glob("./html_pages/SETCO AUTOMOTIVE LTD..html")
#    #files = glob.glob("./html_pages/WELSPUN INDIA LTD..html")
#
#    i=0
#    j=0
#
    #build_files(files)
    # Add stock info to the database
#    build_database(files)
#
#    # All Stocks Excel File
#    all_stk = xlwt.Workbook()
#    ash = all_stk.add_sheet("All Stocks")
#    add_header(ash)
#
#    for stock_page in files:
#        print(stock_page)
#        stock = get_stock_info(stock_page)
#        if not stock:
#            continue
#        if stock.bscs.volume < 50000:
#            continue
#        if stock.bscs.price < 1:
#            continue
#        stock.bscs.price = get_LTP(stock.bscs.symbol)
#        print_stock_info(stock)
#        stock.num.inflation = 0.08
#        stock.num.discount_rate = 0.0
#        stock.num.margin_of_safety = 0.5
#        #Company Excel File
#        com = xlwt.Workbook()
#        calculate_dcf(com, ash, stock)
#        excel = "excel_files/%s.xls" % (stock.bscs.name)
#        PRINT("Writing to %s" % (excel))
#        com.save(excel)
#        j+=1
#
#        stock=None
#        com=None
#        i+=1
#
#    print("Stocks Calculated: %r" %(i))
#    print("Stocks DCF Eligible: %r" %(j))
#    now = datetime.datetime.now()
#    excel = "DCF_Calc/All_Stocks_%s.xls" % (str(now))
#    print("Saving DCF stocks to %s"%(excel))
#    all_stk.save(excel)
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

