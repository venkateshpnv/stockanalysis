import DB
import sys

if __name__ == "__main__":
    new_stocks = DB.build_US_All_Stocks_List()
    sys.exit(0)

    print("Number of new stocks: %r" %(new_stocks))
    DB.build_US_all_stock_information()
    DB.set_sno('US')
    if True:
    #if new_stocks > 1:
        DB.build_US_all_EPS()
        DB.update_US_all_stk_profile()
