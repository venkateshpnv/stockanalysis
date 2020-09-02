import streamlit as st
import DB

mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks_Changes')
query = 'select Date, `Adj Close` from {} order by Date desc limit 1'.format('STKAAPL')
df = DB.read_from_sql(query, mysql_engine)
st.line_chart(df)
DB.close_sql_connection(mysql_engine)
