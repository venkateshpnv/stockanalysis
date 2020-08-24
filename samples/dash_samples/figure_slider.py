import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import pandas as pd
import numpy as np

df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminderDataFiveYear.csv')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    dcc.Graph(id='graph-with-slider'),
    #dcc.Slider(
    #    id='year-slider',
    #    min=df['year'].min(),
    #    max=df['year'].max(),
    #    value=df['year'].min(),
    #    marks={str(year): str(year) for year in df['year'].unique()},
    #    step=None
    #)
    dcc.RangeSlider(
        id='year-slider',
        min=df['year'].min(),
        max=df['year'].max(),
        marks={str(year): str(year) for year in df['year'].unique()},
        step = 1,
        #value = [0, len(df.index)]
        value=[df['year'].min(), df['year'].max()]
         )
])


@app.callback(
    Output('graph-with-slider', 'figure'),
    [Input('year-slider', 'value')])
def update_figure(selected_year):
    #filtered_df = df[df.year == selected_year]
    start=list(np.where(df.year==selected_year[0])[0])[0]
    end=list(np.where(df.year==selected_year[1])[0])[0]
    filtered_df = df.iloc[start:end]

    fig = px.scatter(filtered_df, x="gdpPercap", y="lifeExp", 
                     size="pop", color="continent", hover_name="country", 
                     log_x=True, size_max=55)

    fig.update_layout(transition_duration=500)

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)


