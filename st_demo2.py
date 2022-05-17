# pip install streamlit fbprophet yfinance plotly
import streamlit as st
from datetime import date, timedelta, datetime as dt
from dateutil.relativedelta import relativedelta
import yfinance as yf
#from fbprophet import Prophet
#from fbprophet.plot import plot_plotly
from plotly import graph_objs as go
from plotly.subplots import make_subplots
from DB import *
import pandas as pd
import pandas_ta as ta
import talib
import hdf5
import cufflinks as cf
from webapp import *

padding=0
st.markdown(f""" <style>
.reportview-container .main .block-container{{
    padding-right: {padding}rem;
}} </style> """, unsafe_allow_html=True)

st.title('Stock Forecast App')
st.title('Price Graph')

stocks = ('GOOG', 'AAPL', 'MSFT', 'GME')
stocks = tuple(get_symbols_names_from_mongo())
selected_stock = st.selectbox('Select dataset for prediction', stocks, help="Enter stock symbol or name").split(' ')[0]

#n_years = st.slider('Years of prediction:', 1, 4)
#period = n_years * 365

def _max_width_():
    max_width_str = f"max-width: 95%;"
    #max_width_str = f"max-width: 2000px;"
    st.markdown(
        f"""
    <style>
    .reportview-container .main .block-container{{
        {max_width_str}
    }}
    </style>    
    """,
        unsafe_allow_html=True,
    )

@st.cache
def load_data(ticker):
    mysql_engine = open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Stocks')
    query = 'select Date, Open, High, Low, Volume, `Adj Close` from {}'.format(get_symbol_table_name(ticker))
    data = read_from_sql(query, mysql_engine)
    #data = pd.read_sql_query(query, mysql_engine) 
    #data.reset_index(inplace=True)
    close_sql_connection(mysql_engine)
    return data

data_load_state = st.text('Loading data...')
stk = Stock(selected_stock)
if stk.symbol != selected_stock:
    stk.symbol = selected_stock

print(stk.df)

data = load_data(selected_stock)
#stk =  read_stock_from_mongo(selected_stock)
#url = 'https://www.ti.com/img/logos/US/TXN.png'
#string_logo = '<img src=%s>' % url
#st.markdown(string_logo, unsafe_allow_html=True)

data_load_state.text('Loading data... done!')

#st.subheader('Raw data')
#st.write(data.tail())

duration = relativedelta(years=1)
# Plot raw data
def plot_raw_data():
    global duration
    df = data
    today = dt.now().date()
    st.title('Price Graph')

    #st.markdown(f""" <style>
    #.reportview-container .main .block-container{{
    #    padding-top: {padding}rem;
    #    padding-right: {padding}rem;
    #    padding-left: {padding}rem;
    #    padding-bottom: {padding}rem;
    #}} </style> """, unsafe_allow_html=True)

    #col1,col2,col3,col4,col5,col6,col7,col8,col9 = st.beta_columns([.5, 9])
    #cols = st.columns(9)
    dur_cols = st.columns([1,1,1,1.2,1,1,1,1.2,2,2,4,.5,.5])
    if dur_cols[0].button("1m"):
        duration = relativedelta(months=1)
    if dur_cols[1].button("3m"):
        duration = relativedelta(months=3)
    if dur_cols[2].button("6m"):
        duration = relativedelta(months=6)
    if dur_cols[3].button("YTD"):
        start_date = today.replace(month=1,day=1)
        duration = today - start_date
    if dur_cols[4].button("1y"):
        duration = relativedelta(years=1)
    if dur_cols[5].button("2y"):
        duration = relativedelta(years=2)
    if dur_cols[6].button("5y"):
        duration = relativedelta(years=5)
    if dur_cols[7].button("10y"):
        duration = relativedelta(years=10)
    if dur_cols[8].button("All"):
        duration = -1
    start_date = dt.now().date() - relativedelta(years=1)
    end_date = dt.now().date()
    date_cols = st.columns([3,3,3,3,3])
    start_date = date_cols[0].date_input("Start Date", 
                                            start_date,
                                            #min_value=dt.strptime(stk.df.index[0], "%Y-%m-%d").date(),
                                            #max_value=dt.strptime(stk.df.index[-1], "%Y-%m-%d").date())
                                            min_value=stk.df.index[0].to_pydatetime().date(),
                                            max_value=stk.df.index[-1].to_pydatetime().date())
    end_date = date_cols[2].date_input("End Date", 
                                            end_date, 
                                            #min_value=dt.strptime(stk.df.index[0], "%Y-%m-%d").date(),
                                            #max_value=dt.strptime(stk.df.index[-1], "%Y-%m-%d").date())
                                            min_value=stk.df.index[0].to_pydatetime().date(),
                                            max_value=stk.df.index[-1].to_pydatetime().date())

    st.write(end_date)
    #end = dt.strptime(end_date, "%Y-%m-%d").date()
    end = end_date
    if duration == -1:
        s = 0
        e = hdf5.get_nearest_index(stk.df, end)
    else:
        start = today - duration
        s = hdf5.get_nearest_index(stk.df, start)
        e = hdf5.get_nearest_index(stk.df, end)
    
    #st.write(stk.df.iloc[s:e])
    #fig = go.Figure(
    #        layout={
    #                    "height" : 700,
    #                    "width"  : 2000, 
    #                    #"title" : 'Price Graph',
    #                    "showlegend": True,
    #                }
    #        )
    fig = make_subplots(rows=4, 
                        cols=1, 
                        shared_xaxes=True, 
                        vertical_spacing=0.10, 
                        subplot_titles=('Price', 'Volume', 'RSI', 'Put/Call Ratio'), 
                        row_heights=[1, 0.2, 0.2, 0.2],
                        )

    fig.add_trace(go.Scatter(x=stk.df.iloc[s:e]['Date'], 
                            y=stk.df.iloc[s:e]['Adj Close'], 
                            name="Close",
                            visible = 'legendonly'
                            ),
                            row = 1,
                            col = 1
                )
    fig.add_trace(go.Candlestick(x=stk.df.iloc[s:e].index, 
                                 open = stk.df.iloc[s:e]['Open'],
                                 high = stk.df.iloc[s:e]['High'],
                                 low  = stk.df.iloc[s:e]['Low'],
                                 close = stk.df.iloc[s:e]['Adj Close'],
                                 whiskerwidth=0
                                 ),
                    row = 1,
                    col = 1
                )
    fig.add_trace(go.Bar(x=stk.df.iloc[s:e]['Date'], 
                        y=stk.df.iloc[s:e]['Volume'], 
                        showlegend=False), 
                    row=2, 
                    col=1
                )

    psar = ta.psar(stk.df['High'], stk.df['Low'], stk.df['Adj Close'],af=0.02)
    new_cols={}; new_cols['PSARl_0.02_0.2']='long';new_cols['PSARs_0.02_0.2']='short';new_cols['PSARaf_0.02_0.2']='af';new_cols['PSARr_0.02_0.2']='r'
    psar.rename(columns=new_cols, inplace=True)
    fig.add_trace(go.Scatter(x = psar.iloc[s:e]['long'].dropna().index,
                            y = psar.iloc[s:e]['long'].dropna(),
                            mode = 'markers',
                            marker = dict(size=4),
                            name = 'PSAR long',
                            #fillcolor = 'rgb(0,128,0)'
                            #visible = 'legendonly'
                            ),
                    row=1,
                    col=1
                )
    fig.add_trace(go.Scatter(x = psar.iloc[s:e]['short'].dropna().index,
                            y = psar.iloc[s:e]['short'].dropna(),
                            mode = 'markers',
                            marker = dict(size=4),
                            name = 'PSAR short',
                            #fillcolor = 'rgb(0,128,0)'
                            #visible = 'legendonly'
                            ),
                    row=1,
                    col=1
                )
    ub,mb,lb = talib.BBANDS(df['Adj Close'], timeperiod=20)
    fig.add_trace(go.Scatter(x = ub.iloc[s:e].dropna().index,
                            y = ub.iloc[s:e].dropna(),
                            name = 'BBands upper',
                            line=dict(color="#8AF399"),
                            #line='darkgray',
                            #fillcolor = 'rgb(0,128,0)'
                            #visible = 'legendonly'
                            ),
                    row=1,
                    col=1
                )
    rsi = ta.rsi(df['Adj Close'])
    fig.add_trace(go.Scatter(x = df.iloc[s:e].index,
                            y = rsi.iloc[s:e],
                            name = 'RSI',
                            #line=dict(dash='dot'),
                            #fillcolor = 'rgb(100,128,0)'
                            ),
                    row=3,
                    col=1
                )
    fig.add_trace(go.Scatter(x = stk.put_call_ratios.iloc[s:e].index,
                            y = stk.put_call_ratios.iloc[s:e],
                            name = 'Put/Call Ratios',
                            #line=dict(dash='dot'),
                            #fillcolor = 'rgb(100,128,0)'
                            ),
                    row=4,
                    col=1
                )
 

    fig.update(layout_xaxis_rangeslider_visible=False)
    fig.update_layout(height=1000, width=3500)
    #fig.add_trace(go.Scatter(x=data['Date'], y=data['Adj Close'], name="stock_close"))
    #fig.layout.update(xaxis_rangeslider_visible=True)
    #fig.layout.update(title_text='Time Series data with Rangeslider', xaxis_rangeslider_visible=True)
    #fig.update_xaxes(
    #    rangeslider_visible=True,
    #    rangeselector=dict(
    #        #activecolor="blue",
    #        #bgcolor=colors["background"],
    #        buttons=list(
    #            [
    #                dict(count=7, label="10D",
    #                     step="day", stepmode="backward"),
    #                dict(
    #                    count=15, label="15D", step="day", stepmode="backward"
    #                ),
    #                dict(
    #                    count=1, label="1m", step="month", stepmode="backward"
    #                ),
    #                dict(
    #                    count=3, label="3m", step="month", stepmode="backward"
    #                ),
    #                dict(
    #                    count=6, label="6m", step="month", stepmode="backward"
    #                ),
    #                dict(count=1, label="1y", step="year",
    #                     stepmode="backward"),
    #                dict(count=5, label="5y", step="year",
    #                     stepmode="backward"),
    #                dict(count=1, label="YTD",
    #                     step="year", stepmode="todate"),
    #                dict(step="all"),
    #            ]
    #        ),
    #    ),
    #)
    
    st.plotly_chart(fig)
    
    #st.header('**Price Graph**')
    #layout = cf.Layout(height=700, width=1100)
    #qf=cf.QuantFig(df.iloc[s:e],title='First Quant Figure',legend='top',name='GS', layout=layout)
    #qf.add_bollinger_bands()
    #qf.add_macd()
    #fig = qf.iplot(asFigure=True)
    #fig.layout.update(xaxis_rangeslider_visible=True)
    #st.plotly_chart(fig)

_max_width_()
plot_raw_data()
#
### Predict forecast with Prophet.
##df_train = data[['Date','Close']]
##df_train = df_train.rename(columns={"Date": "ds", "Close": "y"})
##
##m = Prophet()
##m.fit(df_train)
##future = m.make_future_dataframe(periods=period)
##forecast = m.predict(future)
##
### Show and plot forecast
##st.subheader('Forecast data')
##st.write(forecast.tail())
##    
##st.write(f'Forecast plot for {n_years} years')
##fig1 = plot_plotly(m, forecast)
##st.plotly_chart(fig1)
##
##st.write("Forecast components")
##fig2 = m.plot_components(forecast)
##st.write(fig2)
