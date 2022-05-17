#from calculations import calculate_dcf_all_stocks
import DB
import internet
from common import *
from excel import *
from datastructures import Stock
import hdf5
import numpy as np
from sklearn.preprocessing import MinMaxScaler, MaxAbsScaler

def US_main():
    #internet.get_US_stock_page("MSFT")
    #DB.build_US_Stocks_List()
    #internet.get_all_US_html_pages()
    #internet.get_US_stock_page('WM', 'Waste Management, Inc.')
    #internet.send_email_price_changes('US')
    #DB.build_US_database()
    #DB.update_US_all_stock_information()
    #DB.update_US_all_EPS()
    #DB.update_all_stock_betas('India')
    #DB.update_all_US_fin_stmts_errors()
    # Build and update complete information for a new or existing symbol
    #DB.build_US_all_stock_complete_info()
    #DB.update_US_all_EPS()
    #calculate_dcf_all_stocks('US', 5, 'COLD', 'ALL', 'BETA', 'SYNC_DB', 'EXCEL')
    #html_text=internet.get_webpage('https://www.barchart.com/stocks/quotes/SAND/profile')
    #db=DB.open_db('Stocks')
    #DB.update_US_stk_profile(html_text, db.US_Stocks)
    #DB.build_US_All_Stocks_List()
    #DB.build_US_all_stock_information()
    #DB.update_US_all_stk_profile()
    #DB.update_sector_info()
    #internet.price_surprises('US', 0.10, WEEK | DAY, 'COLD', 'SYNC_DB')
    #DB.set_sno('US')
    #DB.update_all_tech_analysis_params('US')
    #DB.update_all_earnings(all=True)
    #DB.update_all_tech_analysis_params(country='US')
    #DB.update_all_price_volume_db('US')
    #DB.update_all_stock_betas('US')
    #DB.clear_all_zero_volume_rows()
    #DB.update_all_since()
    #DB.update_all_earnings_trend()
    DB.update_all_fin_slopes()
    #DB.US_earnings_trends_new_db()
    #DB.update_all_US_fin_percent_change()
    #DB.update_all_tech_analysis_params('US')
    #DB.update_bond_yields()
    #DB.update_US_all_stock_fin_information()
    #internet.update_all_stocks_price_change('US')
    #DB.update_all_put_call_ratios()
    #DB.repopulate_split_stocks()
    #hdf5.insert_all_dfs_from_hdf_to_sql('US')
    #internet.send_email("Hello World")
    #internet.send_email2('petlafin@gmail.com', 'Tasche3#Gm', 'petlafin@gmail.com', 'Test', 'Hello')
    #get_radar_stocks()

    #stock = Stock()
    #url = "https://www.barchart.com/stocks/quotes/AVGO/interactive-chart"
    #internet.browse_US_stock_page(stock, url)
    #DB.build_US_all_earnings_estimates()
US_main()

