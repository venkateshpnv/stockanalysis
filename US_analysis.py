from calculations import calculate_dcf_all_stocks
import DB
import internet

def US_main():
    #internet.get_US_stock_page("MSFT")
    #DB.build_US_Stocks_List()
    #internet.get_all_US_html_pages()
    #internet.get_US_stock_page('WM', 'Waste Management, Inc.')
    #DB.build_US_database()
    #DB.update_all_price_volume_db('US')
    calculate_dcf_all_stocks('US', 5, 'COLD', 'ALL', 'BETA', 'NO_SYNC_DB')
    #html_text=internet.get_webpage('https://www.barchart.com/stocks/quotes/FB/profile')
    #db=DB.open_db('Stocks')
    #DB.update_US_stk_profile(html_text, db.US_Stocks)
    #DB.build_US_All_Stocks_List()
    #DB.build_US_all_stock_information()
    #DB.update_US_all_stk_profile()
    #DB.update_sector_info()
    #internet.price_surprises('US', 0.10, 'ALL')

US_main()

