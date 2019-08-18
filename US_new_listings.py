import DB

if __name__ == "__main__":
    new_stocks = DB.build_US_All_Stocks_List()
    if new_stocks > 0:
        DB.build_US_all_stock_information()
        DB.set_sno('US')
