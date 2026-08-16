import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL to fetch data from
url = "https://www.nasdaq.com/market-activity/earnings"

# Send a GET request to the URL
response = requests.get(url)

# Check if the request was successful
if response.status_code == 200:
    # Parse the HTML content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the table containing the earnings data
    table = soup.find('table')
    
    # Extract table headers
    headers = []
    for th in table.find('thead').find_all('th'):
        headers.append(th.text.strip())

    # Extract table rows
    rows = []
    for tr in table.find('tbody').find_all('tr'):
        cells = tr.find_all('td')
        row = [cell.text.strip() for cell in cells]
        rows.append(row)

    # Create a DataFrame from the extracted data
    df = pd.DataFrame(rows, columns=headers)

    # Display the DataFrame
    print(df)
else:
    print("Failed to fetch the webpage. Status code:", response.status_code)

