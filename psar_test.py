import DB
import pandas as pd
import numpy as np


def webull_like_psar_v2(
    high,
    low,
    close,
    start=0.02,
    increment=0.02,
    maximum=0.20,
):
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)

    idx = high.index
    n = len(high)

    psar = np.full(n, np.nan)
    trend = np.full(n, None, dtype=object)
    af = np.full(n, np.nan)
    ep = np.full(n, np.nan)

    if n < 3:
        return pd.DataFrame(
            {
                "PSAR": psar,
                "PSAR_TREND": trend,
                "AF": af,
                "EP": ep,
            },
            index=idx,
        )

    # Initial trend
    if close.iloc[1] >= close.iloc[0]:
        trend[1] = "up"
        psar[1] = low.iloc[0]
        ep[1] = high.iloc[1]
    else:
        trend[1] = "down"
        psar[1] = high.iloc[0]
        ep[1] = low.iloc[1]

    af[1] = start

    for i in range(2, n):
        prev_trend = trend[i - 1]
        prev_psar = psar[i - 1]
        prev_ep = ep[i - 1]
        prev_af = af[i - 1]

        raw_psar = prev_psar + prev_af * (prev_ep - prev_psar)

        if prev_trend == "up":
            current_psar = min(
                raw_psar,
                low.iloc[i - 1],
                low.iloc[i - 2],
            )

            # Important Webull-like behavior:
            # Do NOT flip down just because today's low/wick goes below SAR.
            # Flip down only when today's CLOSE is below the PREVIOUS SAR.
            if close.iloc[i] < prev_psar:
                trend[i] = "down"
                psar[i] = prev_ep
                ep[i] = low.iloc[i]
                af[i] = start
            else:
                trend[i] = "up"
                psar[i] = current_psar

                if high.iloc[i] > prev_ep:
                    ep[i] = high.iloc[i]
                    af[i] = min(prev_af + increment, maximum)
                else:
                    ep[i] = prev_ep
                    af[i] = prev_af

        else:
            current_psar = max(
                raw_psar,
                high.iloc[i - 1],
                high.iloc[i - 2],
            )

            # Important correction:
            # For bullish recovery, Webull-like behavior matches:
            # Close > CURRENT calculated PSAR.
            # This allows 2026-05-22 to flip up because:
            # Close 154.03 > PSAR 154.003613.
            if close.iloc[i] > current_psar:
                trend[i] = "up"
                psar[i] = prev_ep
                ep[i] = high.iloc[i]
                af[i] = start
            else:
                trend[i] = "down"
                psar[i] = current_psar

                if low.iloc[i] < prev_ep:
                    ep[i] = low.iloc[i]
                    af[i] = min(prev_af + increment, maximum)
                else:
                    ep[i] = prev_ep
                    af[i] = prev_af

    return pd.DataFrame(
        {
            "PSAR": psar,
            "PSAR_TREND": trend,
            "AF": af,
            "EP": ep,
        },
        index=idx,
    )


def add_webull_like_psar_v2(df):
    result = webull_like_psar_v2(
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        start=0.02,
        increment=0.02,
        maximum=0.20,
    )

    df = df.copy()

    df["PSAR"] = result["PSAR"]
    df["PSAR_TREND"] = result["PSAR_TREND"]
    df["AF"] = result["AF"]
    df["EP"] = result["EP"]

    df["WEBULL_LIKE_UPTREND_STARTED"] = (
        (df["PSAR_TREND"].shift(1) == "down")
        & (df["PSAR_TREND"] == "up")
    )

    df["WEBULL_LIKE_DOWNTREND_STARTED"] = (
        (df["PSAR_TREND"].shift(1) == "up")
        & (df["PSAR_TREND"] == "down")
    )

    return df
sym = 'ANET'
mysql_engine = DB.open_sql_connection('localhost', 'root', 'petla123', db='US_Stocks')
params_engine = DB.open_sql_connection('localhost', 'vpetla', 'petla123', db='US_Tech_Params')
query = 'select Date, Open, High, Low, Volume, Close, `Adj Close` from {}'.format(DB.get_symbol_table_name(sym))

df = DB.read_from_sql(query, mysql_engine)
 
df = DB.normalize_cols_with_adj_close(df)
df = add_webull_like_psar_v2(df)

print(df)
