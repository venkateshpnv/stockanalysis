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
    #calculate_dcf_all_stocks('US', 5, 'COLD')
    #html_text=internet.get_webpage('https://www.barchart.com/stocks/quotes/FB/profile')
    #db=DB.open_db('Stocks')
    #DB.update_US_stk_profile(html_text, db.US_Stocks)
    DB.update_US_all_stk_profile()
    #internet.price_surprises('US', 0.10)
    #internet.daily_price_surprises('US', 0.10, 'down')

US_main()

