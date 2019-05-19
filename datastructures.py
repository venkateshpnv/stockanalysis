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
        self.Ratios = Ratios()
        self.Dividend = Dividend()


