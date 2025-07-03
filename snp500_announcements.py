import requests
#from bs4 import BeautifulSoup
import pandas as pd
#from internet import open_browser
#from telegram import get_telegram_chat_id, get_telegram_token_id, notify_message
from datastructures import telegram_tokens
from os import path
from datetime import datetime, time, timedelta, date
import argparse
import time as t
import sys
import time

def get_telegram_token_id(token='stock_notify'):
    if token not in telegram_tokens.keys() or \
            'token' not in telegram_tokens[token].keys() or \
            not path.isfile(telegram_tokens[token]['token']):
        return ""

    token_file = telegram_tokens[token]['token']
    with open(token_file, 'r') as f:
        data = f.read()
        return data.strip()
    return ""

def get_telegram_chat_id(token='stock_notify'):
    if token not in telegram_tokens.keys() or \
            'chat_id' not in telegram_tokens[token].keys() or \
            not path.isfile(telegram_tokens[token]['chat_id']):
        return ""

    token_file = telegram_tokens[token]['chat_id']
    with open(token_file, 'r') as f:
        data = f.read()
        return data.strip()
    return ""

def notify_message(message, token='stock_notify', html='false'):
    if message is None or message == "":
        return

    time.sleep(1)
    chat_id = get_telegram_chat_id(token=token)
    token = get_telegram_token_id(token=token)

    if len(chat_id) == 0 or len(token) == 0:
        print("Invalid token or chat id for %s", token)
        return

    if html:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        resp = requests.post(url, json=payload)
    else:
        url = 'https://api.telegram.org/bot%s/sendMessage?chat_id=%s&text=%s' % (
        token, chat_id, urllib.parse.quote_plus(message))
        resp = requests.get(url, timeout=10)
    #print(resp)
    if resp.status_code != 200:
        print("Failed to send notification with message: %s, err code: %r, err: %r" %(message, resp.status_code, resp.text))
    time.sleep(1)

def fetch_sp_announcements_old():
    #headers = {
    #'User-Agent': (
    #    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    #    '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
    #),
    #'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    #'Accept-Language': 'en-US,en;q=0.5',
    #'Connection': 'keep-alive'
    #}
    try:
        token = get_telegram_token_id(token='sp500_announcement')
        chat_id = get_telegram_chat_id(token='sp500_announcement')
        #headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0'}
        headers = {
                'Host': 'www.spglobal.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Referer': 'https://www.spglobal.com/spdji/en/media-center/news-announcements/',
                'X-Requested-With': 'XMLHttpRequest',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
                'TE': 'trailers',
                }
        #url = "https://www.spglobal.com/spdji/en/media-center/news-announcements"
        #url = "https://www.spglobal.com/spdji/en/media-center/news-announcements/#indexNews"
        url = 'https://www.spglobal.com/spdji/en/util/redesign/press-room/get-pr-news-announcements-solr-json.dot?pageNumber=1&queryText=&contentSubType=indexNews&language_id=1'
        
        ret = requests.get(url, headers=headers)
        if ret.status_code != 200:
            print(f"Failed to fetch the webpage. Status code: {response.status_code}")
            return

        output=ret.json()
        df = pd.DataFrame(output['resultData'])

        df['date'] = pd.to_datetime(df['date']).dt.date
        df.set_index('date', inplace=True)
        base_url = "https://www.spglobal.com"
        df['fullLink'] = base_url + df['link']
        today = date.today() - timedelta(1)
        today_df = df.loc[[today]] if today in df.index else pd.DataFrame()
        if today_df.empty:
            return
        #matches = today_df[today_df['title'].str.contains('Large Cap', case=False, na=False)]
        matches = today_df[today_df['title'].str.contains('Set to Join', case=False, na=False)]
        if not matches.empty:
            for _, row in matches.iterrows():
                title = row['title']
                link = row['fullLink']
                message = f"<b>{title}</b>\n<a href=\"{link}\">Open Link</a>"

                url = f"https://api.telegram.org/bot{token}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                }
                print(f"Matching : {title}")
                response = requests.post(url, json=payload)
                if response.status_code != 200:
                    print("Failed to send message:", response.text)
        else:
            print("No matching news titles found for today.")
        #br = open_browser('headless')
        #br.get(url)
        #soup = BeautifulSoup(br.page_source, "html.parser")
        #announcements = []

        ## Locate the table containing announcements
        #table = soup.find("table")
        #if not table:
        #    print("No table found on the webpage.")
        #    return None

        ## Extract rows from the table
        #rows = table.find_all("tr")
        #for row in rows:
        #    cols = row.find_all("td")
        #    cols = [col.text.strip() for col in cols]
        #    if len(cols) > 0 and "Set to Join" in cols[0]:
        #        announcements.append(cols)

        ## Convert to DataFrame for better handling
        #df = pd.DataFrame(announcements, columns=["Announcement", "Date", "Details"])
        #return df
    except Exception as E:
        print(f"Error : {str(E)}")
        notify_message(f"Error: {str(E)}", token='sp500_announcement')

def fetch_sp_announcements(sent_titles, token, chat_id):
    try:
        headers = {
            'Host': 'www.spglobal.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': 'https://www.spglobal.com/spdji/en/media-center/news-announcements/',
            'X-Requested-With': 'XMLHttpRequest',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'TE': 'trailers',
        }

        url = 'https://www.spglobal.com/spdji/en/util/redesign/press-room/get-pr-news-announcements-solr-json.dot?pageNumber=1&queryText=&contentSubType=indexNews&language_id=1'
        ret = requests.get(url, headers=headers)

        if ret.status_code != 200:
            print(f"Failed to fetch the webpage. Status code: {ret.status_code}")
            return ret.status_code

        output = ret.json()
        df = pd.DataFrame(output['resultData'])

        df['date'] = pd.to_datetime(df['date']).dt.date
        df.set_index('date', inplace=True)
        df['fullLink'] = "https://www.spglobal.com" + df['link']
        today = date.today() #- timedelta(days=1)
        today_df = df.loc[[today]] if today in df.index else pd.DataFrame()

        if today_df.empty:
            print(f"{today}: No announcements found for today.")
            return ret.status_code

        matches = today_df[today_df['title'].str.contains('Set to Join', case=False, na=False)]
        if not matches.empty:
            for i, row in matches.iterrows():
                title = row['title']
                if title in sent_titles:
                    continue  # Skip if already sent
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                link = row['fullLink']
                #message = f"<b>{title}</b>\n<a href=\"{link}\">Open Link</a>"
                message = (
                            f"<b>{title}</b>\n"
                            #f"📅 Date: {i.strftime('%Y-%m-%d')}\n"
                            f"⏰ Sent: {timestamp}\n"
                            f"<a href=\"{link}\">Open Link</a>"
                        )
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                }
                response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload)
                if response.status_code == 200:
                    sent_titles.add(title)
                    print(f"Sent: {title}")
                else:
                    print("Failed to send message:", response.text)
        else:
            print("No matching news titles found for today.")
    except Exception as E:
        print(f"Error : {str(E)}")

    return ret.status_code

def get_diff(time1, time2):
    dt1 = datetime.combine(datetime.today(), time1)
    dt2 = datetime.combine(datetime.today(), time2)
    diff = (dt1 - dt2).total_seconds()
    return diff

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--start_time', type=str, default="15:30", help="Start time in HH:MM format (24-hr)")
    parser.add_argument('--end_time', type=str, default="21:30", help="End time in HH:MM format (24-hr)")
    parser.add_argument('--interval', type=int, default=5, help="Interval in minutes")
    args = parser.parse_args()

    start = datetime.strptime(args.start_time, "%H:%M").time()
    end = datetime.strptime(args.end_time, "%H:%M").time()
    interval = args.interval

    #start = datetime.strptime("15:30", "%H:%M").time()
    #end = datetime.strptime("21:30", "%H:%M").time()
    #interval = 1

    token = get_telegram_token_id(token='sp500_announcement')
    chat_id = get_telegram_chat_id(token='sp500_announcement')

    sent_titles = set()
    sent_failures = set()

    print(f"Monitoring from {start} to {end} every {interval} minutes...")

    while True:
        loop_start_time = t.time()  # record the loop start time in seconds since epoch

        now = datetime.now()
        current_time = now.time()
        today = now.date()
        if current_time < start:
            secs = get_diff(start, current_time)
            secs = int(secs)
            print(f"{now}: Waiting {secs} seconds for start time ({start})... Current time: {current_time}")
            t.sleep(secs)
            continue
        elif start <= current_time <= end:
            print(f"{now}: Checking at {now.strftime('%H:%M:%S')}")
            ret_code = fetch_sp_announcements(sent_titles, token, chat_id)
            if ret_code != 200 and "fail" not in sent_failures:
                interval = 0.5 #half minute
                message = (
                            f"<b>{title}</b>\n"
                            #f"📅 Date: {i.strftime('%Y-%m-%d')}\n"
                            f"⏰ Sent: {timestamp}\n"
                            f"Error: {ret_code} \n"
                            f"<a href=\"{link}\">Open Link</a>"
                        )
                payload = {
                    "chat_id": chat_id,
                    "text": message,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": False
                }
                response = requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json=payload)
                if response.status_code == 200:
                    sent_failures.add("fail")
            else:
                interval = args.interval
                sent_failure = set()
        else:
            print(f"{today}: End time reached ({end}). Exiting.")
            break  # Exit the loop

        # Calculate time taken for the loop iteration
        elapsed = t.time() - loop_start_time
        sleep_duration = max(0, interval * 60 - elapsed)  # ensure no negative sleep
        t.sleep(sleep_duration)

if __name__ == "__main__":
    main()
#if __name__ == "__main__":
#    fetch_sp_announcements()
