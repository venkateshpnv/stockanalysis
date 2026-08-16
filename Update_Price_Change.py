import sys
import internet
import DB
from common import *
import excel
import parse_html
from datetime import datetime as dt
import sys

if __name__ == "__main__":
    #if len(sys.argv) != 2:
    #    print("Invalid arguments")
    #    print("$ %s country_name" %(sys.argv[0]))
    #    sys.exit(1)


    print("Start Time: %r" %(str(dt.now())))
    if is_holiday():
        print("Holiday today")
        sys.exit()

    ## Get today's price from yahoo and update db and hdf5
    try:
       DB.update_all_price_volume_db('US')
    except Exception as e:
        s = parse_html.html_head()
        error = [str(e)]
        s = parse_html.html_text(s, error)
        internet.send_email2(sender_email_id, receiver_email_id, "%s Update Price Volume Error" %(sys.argv[1]), s)

    ### Calculate and store price change
    try:
        internet.update_all_stocks_price_change('US')
    except Exception as e:
        s = parse_html.html_head()
        error = [str(e)]
        s = parse_html.html_text(s, error)
        internet.send_email2(sender_email_id, receiver_email_id, "%s Update Price Change Error" %(sys.argv[1]), s)

    ### Calculate and store technical analysis parameters
    try:
        DB.update_all_tech_analysis_params('US')
    except Exception as e:
        s = parse_html.html_head()
        error = [str(e)]
        print(error)
        s = parse_html.html_text(s, error)
        internet.send_email2(sender_email_id, receiver_email_id, "%s Update Technical Params Error" %(sys.argv[1]), s)

    DB.update_all_stock_betas('US', recession_only=True)

    #try:
    #    DB.update_bond_yields()
    #except Exception as e:
    #    print('Failed to update bond yields')

    DB.update_all_US_fin_percent_change()

    # send email
    try:
        if len(sys.argv) == 2:
            #internet.send_email_price_changes('US')
            #internet.send_email_rsi_changes('US')
            #internet.send_email_trend_changes('US')
            ## Radar Stocks
            excel.get_radar_stocks('US')
    except Exception as e:
        print('Failed to send email, err: %s' %(str(e)))
        pass


    #DB.clear_all_zero_volume_rows()
    #DB.update_all_since()
    #print("End Time: %r" %(str(dt.now())))

