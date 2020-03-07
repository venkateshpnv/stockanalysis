import hdf5
import sys
import parse_html

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid arguments")
        print("$ %s country_name" %(sys.argv[0]))
        sys.exit(1)

    try:
        hdf5.update_percent_change_all(sys.argv[1])
    except Exception as e:
        s = parse_html.html_head()
        error = [str(e)]
        s = parse_html.html_text(s, error)
        internet.send_email2(sender_email_id, sender_passwd, receiver_email_id, "%s Update Percent Change Error" %(sys.argv[1]), s)
