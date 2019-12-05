import DB

if __name__ == "__main__":
    new_stocks = DB.build_US_All_Stocks_List()
    print("Number of new stocks: %r" %(new_stocks))
    if new_stocks > 0:
        DB.build_US_all_stock_information()
        DB.set_sno('US')
        DB.build_US_all_EPS()
        DB.update_US_all_stk_profile()
