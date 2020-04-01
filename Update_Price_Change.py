import sys
import internet
import DB
from common import *
import excel
import parse_html

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid arguments")
        print("$ %s country_name" %(sys.argv[0]))
        sys.exit(1)

    ## Get today's price from yahoo and update db and hdf5
    #try:
    #    DB.update_all_price_volume_db(sys.argv[1])
    #except Exception as e:
    #    s = parse_html.html_head()
    #    error = [str(e)]
    #    s = parse_html.html_text(s, error)
    #    internet.send_email2(sender_email_id, sender_passwd, receiver_email_id, "%s Update Price Volume Error" %(sys.argv[1]), s)

    #### Calculate and store price change
    try:
        internet.update_all_stocks_price_change(sys.argv[1])
    except Exception as e:
        s = parse_html.html_head()
        error = [str(e)]
        s = parse_html.html_text(s, error)
        internet.send_email2(sender_email_id, sender_passwd, receiver_email_id, "%s Update Price Change Error" %(sys.argv[1]), s)
   
    ### send email
    #internet.send_email_price_changes(sys.argv[1])

    ## Radar Stocks
    #if sys.argv[1] == 'US':
    #    excel.get_radar_stocks('US')

    #if sys.argv[1] == 'US':
    #    DB.update_all_stock_betas(sys.argv[1])

