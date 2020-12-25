import DB
import sys
from common import change_vpn

if __name__ == "__main__":
    change_vpn()
    new_stocks = DB.build_US_All_Stocks_List()
    ###print("Number of new stocks: %r" %(new_stocks))
    ### Update sno for all stocks
    DB.set_sno('US')
    ### Get financial statements html pages and build database.
    DB.build_US_all_stock_information()
    #new_stocks=2
    if new_stocks > 0:
        ## Build EPS, Split, Dividend history for all new stocks 
        DB.build_US_all_EPS()
        ## Update stock profile information for all stocks
        #DB.update_US_all_stk_profile()
        ## Update EPS, Split, Dividend history for existing stocks
        #DB.update_US_all_EPS()
        ## Update financial statements with newly populated quarterly, annual statements
        #DB.update_US_all_stock_information()
        ## Update fin percentage changes for all stocks
        #DB.update_all_US_fin_percent_change()
