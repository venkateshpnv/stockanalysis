from dash import html
#import dash_html_components as html
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dashcore
import DB

def get_index_data():
    prices = DB.get_index_prices()

    divs = []
    for k in prices.keys():
        div = html.Div(
                [
                    html.Div(
                        [
                            html.h3(k),
                            html.h4(prices[k]['price']),
                        ],
                    ),
                    html.Div(
                        [
                            html.h4(prices[k]['change']),
                        ],
                    ),
                ]
            )
        divs.append(
                    dbc.Button(children=div, 
                                outline=True, 
                                className="mr-1", 
                                id=k, 
                                size="lg",
                                style = {
                                            'height': '100px',
                                            'width' : '200px',
                                        },
                                )
                    )

    return dbc.ButtonGroup(divs)

def get_header():

    PLOTLY_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
    header = html.Div(
        [
            html.Br([]),

            html.Div(
                [
                    html.Img(
                        src=PLOTLY_LOGO,
                        #src=app.get_asset_url("dash-financial-logo.png"),
                        className="logo",
                        #height="40px",
                        style={
                            'height': '100px',
                            'float': 'left'
                        },
                    ),
                    #html.H2(
                    #    "Stock Analyser",
                    #    style={'marginTop': 20, 'marginBottom': 20}
                    #),
                    html.H2('Stock Analyser',
                            style={'display': 'inline',
                                    'float': 'left',
                                    'font-size': '2.65em',
                                    'margin-left': '7px',
                                    'font-weight': 'bolder',
                                    'font-family': 'Product Sans',
                                    'color': "rgba(117, 117, 117, 0.95)",
                                    'margin-top': '20px',
                                    'margin-bottom': '0'
                                    }
                            ),

                ],
                className="row",
            ),
            html.Div(
                [
                    get_index_data(),
                    #html.Div(
                    #    [html.H5("Calibre Financial Index Fund Investor Shares")],
                    #    className="seven columns main-title",
                    #),
                    #html.Div(
                    #    [
                    #        dcc.Link(
                    #            "Full View",
                    #            href="/dash-financial-report/full-view",
                    #            className="full-view-link",
                    #        )
                    #    ],
                    #    className="five columns",
                    #),
                ],
                className="twelve columns",
                style={"padding-left": "0"},
            ),
        ],
        className="row",
    )
    return header

def get_menu():
    menu = html.Div(
        [
            dcc.Link(
                "Overview",
                href="/dash-financial-report/overview",
                className="tab first",
            ),
            dcc.Link(
                "Price Performance",
                href="/dash-financial-report/price-performance",
                className="tab",
            ),
            dcc.Link(
                "Portfolio & Management",
                href="/dash-financial-report/portfolio-management",
                className="tab",
            ),
            dcc.Link(
                "Fees & Minimums", href="/dash-financial-report/fees", className="tab"
            ),
            dcc.Link(
                "Distributions",
                href="/dash-financial-report/distributions",
                className="tab",
            ),
            dcc.Link(
                "News & Reviews",
                href="/dash-financial-report/news-and-reviews",
                className="tab",
            ),
        ],
        className="row all-tabs",
    )
    return menu

def get_search_bar(db):
    search_bar = dbc.Row(
        [
            dbc.Col(dbc.Input(id=db.com['sym']['input'], 
                            type="search",
                            list=db.com['sym']['suggest'],
                            placeholder="Enter a Stock Symbol",
                            size='30',
                            value=''
            )),
            dbc.Col(
                dbc.Button("Search",
                           color="primary", 
                           className="ml-2",
                           id=db.com['sym']['button']
                          ),
                width="auto",
            ),
        ],
        no_gutters=True,
        className="ml-auto flex-nowrap mt-3 mt-md-0",
        align="center",
    )
    return search_bar

def Header(db):
    return html.Div([get_header(), html.Br([]), get_search_bar(db)])

def make_dash_table(df):
    """ Return a dash definition of an HTML table for a Pandas dataframe """
    table = []
    for index, row in df.iterrows():
        html_row = []
        for i in range(len(row)):
            html_row.append(html.Td([row[i]]))
        table.append(html.Tr(html_row))
    return table

