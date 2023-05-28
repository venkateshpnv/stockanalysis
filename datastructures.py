from dateutil.relativedelta import relativedelta
from datetime import datetime as dt

class Basics:
    def __init__(self):
        self.name   = 'DEADCOW'
        self.symbol = 'DEAD'
        self.bse_symbol = 'DEAD'
        self.sector = 'DEAD'
        self.industry = 'DEAD'
        self.price  = 0
        self.price_years = 0
        self.hist_price_5 = 0
        self.hist_price_10 = 0
        self.promoter_stake = 0
        self.corp_stake     = 0
        self.pub_stake      = 0
        self.fii_stake      = 0
        self.dii_stake      = 0
        self.others_stake   = 0
        self.face_value     = 0
        self.volume         = 0
        self.mcap           = 0
        self.outstanding_shares = 0
        self.split_date     = 0
        self.split_year     = 0
        self.split_factor   = 1
        self.five_yr_beta = 0
        self.float = 0
        self.float_percent = 0
        self.trading = 'YES'
        self.fiftytwoweek_high=0
        self.fiftytwoweek_low=0

class Ratios:
    def __init(self):
        self.interest_coverage = 0
        self.forward_PE = 0
        self.ttm_PE = 0
        self.conf.ROE = 0
        # Percentages
        self.conf.ROA = 0
        #self.conf.ROCE = 0
        self.GPM = 0
        self.NPM = 0
        # Debt/Equity
        self.DtoE = 0
        self.PtoB = 0
        self.BOOK = 0
        
class Dividend:
    def __init(self):
        self.yld = 0
        self.payout_ratio = 0

class Quart_EPS:
    def __int(self):
        self.date = ''
        self.price = 0
        self.eps = 0

class Figures:
    # row 0 - year
    # row 1 - sales
    # row 2 - profit
    # row 3 - free cash flow
    # row 4 - book value
    # 20 years of data of sales, profit etc
    #entries = [[0] * MAX_Years for i in range(indices)]
    #entries = list()
    #entries = list()
    # number of years of data we have for each field.
    # ex: 10 years of book value, 8 years of cash flow etc.
    #fig_years = [0] * (indices)
    #fig_years = []
    Years = []
    Sales = []
    PBT = []
    PAT = []
    INTEREST = []
    Taxes = []
    EBIT = []
    PAT_M = []
    EPS = []
    BOOK = []
    LIABILITIES = []
    DEBT = []
    ASSETS = []
    EQUITY = []
    SHARES = []
    CASH = []
    PPE = []
    DEPRECIATION = []
    CAPEX = []
    ROA = []
    ROE = []
    ROCE = []
    DtoE = []
    INTR = []


    def __init__(self):
        self.ttm_eps = 0
        # Long Term Debt
        #self.lt_debt = 0
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0
        self.price_growth = 0
        self.growth = 0
        self.common_shares = 0
        #self.entries = [[0 for i in range(1)] for j in range(indices)]
        self.Years = []
        self.Sales = []
        self.PBT = []
        self.INTEREST = []
        self.PAT = []
        self.Taxes = []
        self.EBIT = []
        self.PAT_M = []
        self.EPS = []
        self.QUART_EPS = Quart_EPS()
        self.BOOK = []
        self.LIABILITIES = []
        #self.DEBT = []
        self.ASSETS = []
        self.EQUITY = []
        self.SHARES = []
        self.CASH = []
        self.PPE = []
        self.DEPRECIATION = []
        self.CAPEX = []
        self.ROA = []
        self.ROE = []
        self.ROCE = []
        self.DtoE = []
        self.INTR = []

    def __del__(self):
        self.ttm_eps = 0
        # Long Term Debt
        #self.lt_debt = 0
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0
        self.growth = 0
        #self.entries = [[0 for i in range(1)] for j in range(indices)]
        self.Years.clear()
        self.Sales.clear()
        self.PBT.clear()
        self.PAT.clear()
        self.Taxes.clear()
        self.INTEREST.clear()
        self.EBIT.clear()
        self.PAT_M.clear()
        self.EPS.clear()
        self.BOOK.clear()
        self.LIABILITIES.clear()
        #self.DEBT = []
        self.ASSETS.clear()
        self.EQUITY.clear()
        self.SHARES.clear()
        self.CASH.clear()
        self.PPE.clear()
        self.DEPRECIATION.clear()
        self.CAPEX.clear()
        self.ROA.clear()
        self.ROE.clear()
        self.ROCE.clear()
        self.DtoE.clear()
        self.INTR.clear()

class Quarterly_Figures:
    # row 0 - year
    # row 1 - sales
    # row 2 - profit
    # row 3 - free cash flow
    # row 4 - book value
    # 20 years of data of sales, profit etc
    #entries = [[0] * MAX_Years for i in range(indices)]
    #entries = list()
    #entries = list()
    # number of years of data we have for each field.
    # ex: 10 years of book value, 8 years of cash flow etc.
    #fig_years = [0] * (indices)
    #fig_years = []
    Quarters = []
    Sales = []
    PBT = []
    PAT = []
    INTEREST = []
    Taxes = []
    EBIT = []
    PAT_M = []
    BASIC_EPS = []
    BASIC_CONT_EPS = []
    DILUTED_EPS = []
    DILUTED_CONT_EPS = []
    BOOK = []
    LIABILITIES = []
    DEBT = []
    ASSETS = []
    EQUITY = []
    SHARES = []
    CASH = []
    PPE = []
    DEPRECIATION = []
    CAPEX = []
    ROA = []
    ROE = []
    ROCE = []
    DtoE = []
    INTR = []


    def __init__(self):
        self.ttm_eps = 0
        # Long Term Debt
        #self.lt_debt = 0
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0
        self.price_growth = 0
        self.growth = 0
        self.common_shares = 0
        #self.entries = [[0 for i in range(1)] for j in range(indices)]
        self.Quarters = []
        self.Sales = []
        self.PBT = []
        self.INTEREST = []
        self.PAT = []
        self.Taxes = []
        self.EBIT = []
        self.PAT_M = []
        self.BASIC_EPS = []
        self.BASIC_CONT_EPS = []
        self.DILUTED_EPS = []
        self.DILUTED_CONT_EPS = []
        self.BOOK = []
        self.LIABILITIES = []
        #self.DEBT = []
        self.ASSETS = []
        self.EQUITY = []
        self.SHARES = []
        self.CASH = []
        self.PPE = []
        self.DEPRECIATION = []
        self.CAPEX = []
        self.ROA = []
        self.ROE = []
        self.ROCE = []
        self.DtoE = []
        self.INTR = []

    def __del__(self):
        self.ttm_eps = 0
        # Long Term Debt
        #self.lt_debt = 0
        self.sales_growth  = 0
        self.profit_growth = 0
        self.cash_growth = 0
        self.book_growth = 0
        self.growth = 0
        #self.entries = [[0 for i in range(1)] for j in range(indices)]
        self.Quarters.clear()
        self.Sales.clear()
        self.PBT.clear()
        self.PAT.clear()
        self.Taxes.clear()
        self.INTEREST.clear()
        self.EBIT.clear()
        self.PAT_M.clear()
        self.BASIC_EPS.clear()
        self.BASIC_CONT_EPS.clear()
        self.DILUTED_EPS.clear()
        self.DILUTED_CONT_EPS.clear()
        self.BOOK.clear()
        self.LIABILITIES.clear()
        #self.DEBT = []
        self.ASSETS.clear()
        self.EQUITY.clear()
        self.SHARES.clear()
        self.CASH.clear()
        self.PPE.clear()
        self.DEPRECIATION.clear()
        self.CAPEX.clear()
        self.ROA.clear()
        self.ROE.clear()
        self.ROCE.clear()
        self.DtoE.clear()
        self.INTR.clear()


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

    dcf_years = 0
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

class Price_Change:
    def __init__(self):
        self.year = 0
        self.quarter = 0
        self.month = 0
        self.week = 0
        self.day = 0

class Earnings_History:
    def __init__(self):
        self.quarters=[]
        self.reported=[]
        self.estimate=[]
        self.difference=[]
        self.surprise=[]

class Earnings_Estimates:
    def __init__(self):
        self.quarters=[]
        self.years=[]
        self.q_avg_est=[]
        self.q_num_est=[]
        self.q_high_est=[]
        self.q_low_est=[]
        self.q_prior_yr=[]
        self.q_gr_rate=[]

        self.y_avg_est=[]
        self.y_num_est=[]
        self.y_high_est=[]
        self.y_low_est=[]
        self.y_prior_yr=[]
        self.y_gr_rate=[]

class Earnings:
    def __init__(self):
        self.date=""
        self.high_target=0
        self.mean_target=0
        self.low_target=0
        self.hist= Earnings_History()
        self.est = Earnings_Estimates()

class Stock:
    def __init__(self):
        self.bscs = Basics()
        self.num  = Numbers()
        self.fig  = Figures()
        self.quart_fig  = Quarterly_Figures()
        self.Ratios = Ratios()
        self.Dividend = Dividend()
        self.price_change = Price_Change()
        self_earnings = Earnings()
        self.sno=0

recessions = { 
                "1990" : { "start" : "16 July 1990",
                           "end" : "14 January 1991",
                           "duration" : 8
                         },
                "2001" : { "start" : "31 August 2000",
                           "end" : "12 March 2003",
                           "duration" : 31
                         },
                "2007" : { "start" : "12 October 2007",
                           "end" : "27 February 2009",
                           "duration" : 14
                         },
                "2018" : { "start" : "30 November 2018",
                           "end" : "21 December 2018",
                           "duration" : 1
                         },
                "2020" : { "start" : "19 February 2020",
                           "end"   : "23 March 2020",
                           "duration" : 1
                         },
                "2021" : { "start" : "24 November 2021",
                         },
 
             }

crypto_symbols = ['BTC', 'ETH']

major_exchanges = ['NASDAQ', 'NYSE', 'NYSE MKT', 'NYSE ARCA', 'AMEX']

#select DISTINCT Exchange from US_Stocks_Data.US_All_Stocks_List order  by Exchange;
all_exchanges = ['AMEX', 'BATS', 'EXPM', 'LSE', 'NASDAQ', 'NMFQS', 'NYSE', 'NYSE ARCA', 'NYSE MKT', 'OTC', 'OTCBB', 'OTCCE', 'OTCGREY', 'OTCMKTS', 'OTCQB', 'OTCQX', 'PINK', 'US', 'NasdaqCM', 'NasdaqGM', 'NasdaqGS', 'NYSE American', ]

#all_exchanges = ['NYSE', 'NASDAQ', 'AMEX', 'BATS', 'OTCQB', 'PINK', 'OTCQX', 'OTCMKTS', 'NMFQS', 'NYSE MKT','OTCBB', 'OTCGREY', 'BATS', 'OTC']

India_indices = {'^BSESN': 'BSE', '^NSEI':'NSE'}
US_indices = {'GSPC':'SP500', 'DJI': 'DowJones', 'IXIC': 'Nasdaq', 'RUT': 'Russel2000'} 
#US_indices = {'^GSPC':'SP500', '^DJI': 'DowJones', '^IXIC': 'Nasdaq', '^RUT': 'Russel2000'} 
Treasury_Yields = {'^FVX' : 'TYield_5Years', '^TNX' : 'TYield_10Years', '^TYX' : 'TYield_30Years'}

treasury_yield_urls = {
                        'whole' : 'https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/TextView.aspx?data=yieldAll',
                        'year'  : 'https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/TextView.aspx?data=yieldYear&year=YEAR_YOU_WANT',
                        'month' : 'https://www.treasury.gov/resource-center/data-chart-center/interest-rates/pages/TextView.aspx?data=yield',
                    }

price_fields = {'Date':'varchar(12)', 
                'High':'float', 
                'Low':'float', 
                'Open':'float', 
                'Close':'float', 
                'Volume':'BIGINT UNSIGNED', 
                'Adj Close':'float', 
                'Short':'BIGINT UNSIGNED',
                }
price_fields_datatypes = ['varchar(12)', 'float', 'float', 'float', 'float', 'BIGINT UNSIGNED', 'float', 'BIGINT UNSIGNED']

price_change_fields = {'Day Change':'float', 
                        'Week Change':'float',
                        'Two Week Change':'float',
                        'Month Change':'float',
                        'Quarter Change':'float',
                        'Half Year Change':'float', 
                        'Year Change':'float', 
                        'Five Year Change':'float', 
                        'Ten Year Change':'float', 
                        'Whole Change':'float',
                        'YTD Change':'float',
                        }

price_change_fields_datatypes = ['float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float']
price_change_durations = [relativedelta(days=1), relativedelta(weeks=1), relativedelta(weeks=2), relativedelta(months=1), relativedelta(months=3), relativedelta(months=6), relativedelta(years=1), relativedelta(years=5), relativedelta(years=10)]

beta_change_fields = {'One_Month':relativedelta(months=1), 
                        'Three_Months':relativedelta(months=3), 
                        'Six_Months':relativedelta(months=6),
                        'Year':relativedelta(years=1),
                        'Five_Year':relativedelta(years=5),
                        'Whole': dt.now().date() - dt.strptime("1970-01-01", "%Y-%m-%d").date(),
                    }
#beta_change_fields = ['One_Month_Beta', 'Three_Months_Beta', 'Six_Months_Beta', 'Year_Beta', 'Five_Year_Beta', 'Ten_Year_Beta', 'Whole_Beta']
beta_change_durations = [relativedelta(months=1), relativedelta(months=3), relativedelta(months=6), relativedelta(years=1), relativedelta(years=5)]
beta_parameters = ['beta', 'volatility', 'momentum']
#beta_parameters = ['Start_Price', 'End_Price', 'Start_Date', 'End_Date', 'Index_CAGR', 'Index_Percent_Change', 'CAGR', 'Percent_Change', 'beta', 'alpha', 'alpha_pure', 'r_squared', 'volatility', 'avg_price']

fin_year_fields = {'yoy':'float', 
                    'yo3y':'float',
                    'yo5y':'float',
                    'yo10y':'float',
                    'yowy':'float',
                    }
fin_year_fields_datatypes = ['float', 'float', 'float', 'float', 'float']
fin_year_price_durations = [relativedelta(years=1), relativedelta(years=3), relativedelta(years=5), relativedelta(years=10)]

fin_quarter_fields = {'qoq':'float',
                        'qo2q':'float', 
                        'qo4q':'float', 
                        'qo6q':'float', 
                        'qowq':'float',
                        }
fin_quarter_fields_datatypes = ['float', 'float', 'float', 'float', 'float']
fin_quarter_price_durations = [relativedelta(months=3), relativedelta(months=6), relativedelta(months=12), relativedelta(months=24)]

#income_fields = {'Sales':'float', 
#                    'Gross Profit':'float', 
#                    'Net Income $M':'float', 
#                    'EPS Diluted Continuous Ops':'float',
#                    }
#balance_fields = {'Cash & Cash Equivalents':'float', 
#                    'Total Current Assets':'float', 
#                    'Total Non-Current Assets':'float',
#                    'Total Assets $M':'float', 
#                    'Total Current Liabilities':'float', 
#                    'Total Non-Current Liabilities':'float', 
#                    'Total liabilities':'float', 
#                    'Common Shares':'BIG INT', 
#                    'Total Liabilities And Equity':'float',
#                    }
#cash_fields = {'Beginning Cash Position':'float', 
#                'End Cash Position':'float', 
#                'Free Cash Flow':'float', 
#                'Change In Cash':'float',
#                }

income_fields = {'costOfRevenue':'float',
                    'grossProfit':'float',
                    'netIncome':'float',
                    'totalRevenue':'float',
                }
balance_fields = {'totalAssets':'float',
                    'totalCurrentAssets':'float',
                    'totalLiab':'float',
                    'totalCurrentLiabilities':'float',
                    'longTermDebtTotal':'float',
                }
cash_fields = {'freeCashFlow':'float',
                'endPeriodCashFlow':'float',
                'changeInCash':'float',
                'totalCashflowsFromInvestingActivities':'float',
                }
generic_fields = {'Symbol':'varchar(12)',
                    'IsDelisted': 'BOOL',
                    'Date':'varchar(12)',
                    'report_date':'varchar(12)',
                    'before_after_market':'varchar(25)',
                    'SPLIT':'varchar(12)',
                    'contractSymbol':'varchar(12)', 
                    'lastTradeDate':'varchar(12)', 
                    'strike':'float', 
                    'lastPrice':'float', 
                    'bid':'float', 
                    'ask':'float', 
                    'change':'float', 
                    'percentChange':'float', 
                    'volume':'UNSIGNED BIGINT', 
                    'openInterest':'float', 
                    'impliedVolatility':'float', 
                    'inTheMoney':'BOOL', 
                    'contractSize':'UNSIGNED INT', 
                    'currency':'varchar(12)', 
                    'currency_symbol':'varchar(12)', 
                    'filing_date':'varchar(12)', 
                    'Stock Splits':'varchar(20)', 
                    'period':'varchar(15)', 
                    'paymentDate':'varchar(12)', 
                    'declarationDate':'varchar(12)', 
                    'recordDate':'varchar(12)', 
                    'MostRecentQuarter':'varchar(12)', 
                    'DividendDate':'varchar(12)', 
                    'ExDividendDate':'varchar(12)', 
                    'LastSplitDate':'varchar(12)', 
                    'dateFormatted':'varchar(12)', 
                    'sharesMln': 'BIG INT', 
                    'shares': 'BIG INT', 
                    'LastSplitFactor':'varchar(20)',
                    'Holiday':'text',
                    'Type':'text',
                    }
generic_fields_datatypes = ['varchar(12)', 'varchar(12)','varchar(12)', 'varchar(24)', 'varchar(24)', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'float', 'BOOL', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(20)', 'varchar(15)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'varchar(12)', 'BIGINT', 'BIGINT', 'varchar(12)']

trends_fields = {'date'  : 'varchar(12)', 
                'period' : 'varchar(12)', 
                'growth' : 'float', 
                'earningsEstimateAvg' : 'float', 
                'earningsEstimateLow' : 'float', 
                'earningsEstimateHigh': 'float',
                'earningsEstimateYearAgoEps' : 'float', 
                'earningsEstimateNumberOfAnalysts' : 'int', 
                'earningsEstimateGrowth' : 'float', 
                'revenueEstimateAvg' : 'float', 
                'revenueEstimateLow' : 'float', 
                'revenueEstimateHigh': 'float', 
                'revenueEstimateYearAgoEps' : 'float', 
                'revenueEstimateNumberOfAnalysts' : 'int', 
                'revenueEstimateGrowth' : 'float', 
                'epsTrendCurrent' : 'float', 
                'epsTrend7daysAgo' : 'float', 
                'epsTrend30daysAgo': 'float', 
                'epsTrend60daysAgo': 'float',
                'epsTrend90daysAgo': 'float',
                'epsRevisionsUpLast7days' : 'float', 
                'epsRevisionsUpLast30days': 'float', 
                'epsRevisionsDownLast30days' : 'float',
                }

#Ticker info fields in the US_Stocks.STKSYMBOL.
# This information is retrieved from yfinance.Ticker(SYMBOL).info() and updated in our tables on daily basis.
tick_fields = ['floatShares', 'heldPercentInsiders', 'heldPercentInstitutions', 'sharesOutstanding', 'sharesPercentSharesOut', 'sharesShort', 'sharesShortPreviousMonthDate', 'sharesShortPriorMonth', 'shortPercentOfFloat', 'shortRatio']
tick_share_holders = ['percent_insider', 'percent_institution', 'float_percent_institution', 'num_institutions']

other_tables = ['BOND_YIELDS']

# Treasury Bills - Maturity rate between 4 weeks and a year
# Treasury Notes - Maturity rate between 2 years and 10 years
# Treasury Bonds - Maturity rate between 10 years and 30 years

# Federal Reserve Economic Data
fred = {
        'treasury': {

                        # Ten year treasury yield
                        # Units: percent
                        # Frequency: Daily
                        'ten_year_yield': 'T10YFF',
                    },
        'interest_rates' : {
                            
                        },

        # Monthly parameters
            'interest_rates':'INTDSRUSM193N', 
            'unemployment_rate': 'UNRATE',

            # Total Nonfarm Payroll, is a measure of the number of U.S. workers 
            # in the economy that excludes proprietors, private household employees, 
            # unpaid volunteers, farm employees, and the unincorporated self-employed. 
            # This measure accounts for approximately 80 percent of the workers 
            # who contribute to Gross Domestic Product (GDP).
            # Units: The data is in thousands.
            'monthly_payroll_change': 'PAYEMS', 

            # 
            'fed_fund_rate' : 'FEDFUNDS',

        # Quarterly parameters
            'gdp':'GDP',
            'gdp_percent_change': 'A191RL1Q225SBEA',
            'real_gdp': 'GDPC1',
        }
# paths
radar_stocks_file='/home/vpetla/work/stockanalysis/US_Stocks/DCF_Calc/radar_stocks.xls'
pp_file='/home/vpetla/PP.csv'

# EOD Token file
eod_token_file='/home/vpetla/eod_token_file.txt'

