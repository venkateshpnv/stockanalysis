##declare.py

#Total Companies
COUNT=0

# Price change count in excel
PR_COUNT=0
PR_YR_COUNT=0
PR_QR_COUNT=0
PR_MON_COUNT=0
PR_WEEK_COUNT=0
PR_DAY_COUNT=0

#Indexes of entries in All_Stocks.xls
COMP=0
SYM=0
SEC=0
IND=0
SINCE=0
CUR_PR_DT=0
CUR_PR=0
F2WK_HG=0
F2WK_LW=0
W_F2WK_HG=0
W_F2WK_LO=0
DCF_PR=0
MOS_PR=0
SAL_PR=0
MOS_RT=0
CUR_RT=0
VOL=0
YR_DAT=0
PRICE_YR_DAT=0
TEN_PRICE=0
TEN_SAL=0
TEN_PR=0
TEN_BK=0
TEN_CSH=0
FIVE_SAL=0
FIVE_PR=0
FIVE_BK=0
FIVE_CSH=0
THREE_SAL=0
THREE_PR=0
THREE_BK=0
THREE_CSH=0
FV=0
WEBSITE_BETA=0
BETA=0
ONE_BETA=0
THREE_BETA=0
SIX_BETA=0
YEAR_BETA=0
FIVE_BETA=0
PE=0
TTM_PE=0
NPM=0
DTOTE=0
INT_C=0
ROE=0
ROA=0
ROCE=0
MCAP=0
REVENUE=0
FII=0
DII=0
R2007_BETA=0
R2007_ALPHA=0
R2007_PURE_ALPHA=0
R2007_IPER_CHG=0
R2007_PER_CHG=0
SINCE_LAST_PER_CHG=0
R2007_CAGR=0
R2007_ICAGR=0
R2020=0
W_BETA=0
W_ALPHA=0
W_PURE_ALPHA=0
PRM_S=0
FLT=0
FLT_PER=0
RSI=0
RSI_MIN_DIFF=0
RSI_MAX_DIFF=0
RSI_60_MAX=0
RSI_DIFF=0
RSI_PRICE_CHANGE=0
RSI_PRICE_CHANGE_DAYS=0
MSTAR=0
BBANDS_RANGE=0
WH_PR_CHANGE=0
YR_PR_CHANGE=0
HF_YR_PR_CHANGE=0
QR_PR_CHANGE=0
MON_PR_CHANGE=0
WEEK_PR_CHANGE=0
TWO_WEEK_PR_CHANGE=0
DAY_PR_CHANGE=0
VOLATILITY=0
ONE_MOMENTUM=0
THREE_MOMENTUM=0
SIX_MOMENTUM=0

MAX_Years = 20

#Sales, PAT, Cash Flow, Book Value
GROWTH_PARAMS = 4

# Number of figures we are tracking data for.
indices=0
Years = indices
indices+=1
Sales = indices
indices+=1
#Profit Before Taxes
PBT = indices
indices+=1
Taxes = indices
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
bse_stocks="India_Stocks/BSE_Stocks.xls"
#nyse_stocks = "US_Stocks/NYSE_Stocks.xls"
#nasdaq_stocks = "US_Stocks/NASDAQ_Stocks.xls"
#amex_stocks = "US_Stocks/AMEX_Stocks.xls"

nyse_stocks = "/tmp/nyse.csv"
nasdaq_stocks = "/tmp/nasdaq.csv"
amex_stocks = "/tmp/amex.csv"

# Percentage change in growth over a period of time
gr1to5_percent   = 1
gr6to8_percent   = 0.7
gr9to10_percent  = 0.8
gr11to15_percent = 0.5
gr16to20_percent = 0.8


def init_variables():
    CONF=0
    COMP=0
    SYM=0
    SINCE=0
    CUR_PR_DT=0
    CUR_PR=0
    F2WK_HG=0
    F2WK_LW=0
    W_F2WK_HG=0
    W_F2WK_LO=0
    DCF_PR=0
    MOS_PR=0
    SAL_PR=0
    MOS_RT=0
    CUR_RT=0
    VOL=0
    YR_DAT=0
    PRICE_YR_DAT=0
    TEN_PRICE=0
    TEN_SAL=0
    TEN_PR=0
    TEN_BK=0
    TEN_CSH=0
    FIVE_SAL=0
    FIVE_PR=0
    FIVE_BK=0
    FIVE_CSH=0
    THREE_SAL=0
    THREE_PR=0
    THREE_BK=0
    THREE_CSH=0
    FV=0
    WEBSITE_BETA=0
    BETA=0
    ONE_BETA=0
    THREE_BETA=0
    SIX_BETA=0
    YEAR_BETA=0
    FIVE_BETA=0
    TTM_PE=0
    NPM=0
    DTOTE=0
    INT_C=0
    ROE=0
    ROA=0
    ROCE=0
    MCAP=0
    REVENUE=0
    FII=0
    DII=0
    PRM_S=0
    R2007_BETA=0
    R2007_ALPHA=0
    R2007_PURE_ALPHA=0
    R2007_IPER_CHG=0
    R2007_PER_CHG=0
    SINCE_LAST_PER_CHG=0
    R2007_CAGR=0
    R2007_ICAGR=0
    R2020=0
    W_BETA=0
    W_ALPHA=0
    W_PURE_ALPHA=0
    FLT=0
    FLT_PER=0
    RSI=0
    RSI_MIN_DIFF=0
    RSI_MAX_DIFF=0
    RSI_60_MAX=0
    RSI_DIFF=0
    RSI_PRICE_CHANGE=0
    RSI_PRICE_CHANGE_DAYS=0
    BBANDS_RANGE=0
    MSTAR=0
    WH_PR_CHANGE=0
    YR_PR_CHANGE=0
    HF_YR_PR_CHANGE=0
    QR_PR_CHANGE=0
    MON_PR_CHANGE=0
    WEEK_PR_CHANGE=0
    TWO_WEEK_PR_CHANGE=0
    DAY_PR_CHANGE=0
    VOLATILITY=0
    ONE_MOMENTUM=0
    THREE_MOMENTUM=0
    SIX_MOMENTUM=0

    SEC=0
    IND=0

    PE=0
    F_PE=0 # Forward PE
    PB=0
    PBMRQ=0 # Price to Book Most Recent Quarter
    #PS=0
    PSTTM=0
    PEG=0
    BOOK=0
    
    FIFTY_DAY_MA=0
    TWO_HUNDRED_DAY_MA=0

    EPS=0
    EPS_ESTIMATE_CUR_YR=0
    EPS_ESTIMATE_NEXT_YR=0
    RPS_TTM=0 # Revenue per share TTM
    PPS_TTM=0 # Profit per share TTM
    GROSS_PROFIT_TTM=0
    PROFIT_MARGIN=0
    OPER_MARGIN_TTM=0
    QUART_REV_GROWTH_YOY=0
    QUART_EARNINGS_GROWTH_YOY=0
    DIV=0 # Dividend Rate
    DIV_PAY=0 # Dividend Payout Ratio

    SHORT_RATIO=0
    SHARES_FLOAT_PERCENT=0
    #SHARES_SHORT=0
    SHORT_PERCENT_FLOAT=0
    SHORT_PERCENT_OUTSTANDING=0
    SHORT_PRIOR_MONTH=0

    WALLST_TARGET_PRICE=0 # Wallstreet target price
    ANALYST_TARGET_PRICE=0
    ANALYST_RATING=0
    STRONG_BUY=0
    #BUY=0
    #HOLD=0
    #SELL=0
    STRONG_SELL=0

    PERCENT_INSIDERS=0
    PERCENT_INSTITUTIONS=0

    
    MAX_Years = 20
    #Sales, PAT, Cash Flow, Book Value
    GROWTH_PARAMS = 4
    
    # Number of figures we are tracking data for.
    indices=0

    PR_COUNT=0
    PR_YR_COUNT=0
    PR_QR_COUNT=0
    PR_MON_COUNT=0
    PR_WEEK_COUNT=0
    PR_DAY_COUNT=0


