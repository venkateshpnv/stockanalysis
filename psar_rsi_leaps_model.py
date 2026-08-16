import argparse
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import talib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import inspect, text


ACTION_HOLD = 0
ACTION_BUY_CALL = 1
ACTION_BUY_PUT = 2
ACTION_NAME = {
    ACTION_HOLD: "HOLD",
    ACTION_BUY_CALL: "BUY_CALL",
    ACTION_BUY_PUT: "BUY_PUT",
}


@dataclass
class DBConfig:
    host: str
    db: str
    user: str = "vpetla"
    password: str = "petla123"
    port: int = 3306


@dataclass
class StrategyConfig:
    rsi_period: int = 14
    rsi_window: int = 60
    lookahead_days: int = 20
    rsi_proximity: float = 0.15
    buy_forward_return: float = 0.08
    sell_forward_return: float = 0.08
    max_dte_days: int = 60
    dte_window_days: int = 45


@dataclass
class TrainConfig:
    n_estimators: int = 400
    max_depth: int = 10
    min_samples_leaf: int = 20
    random_state: int = 42


def to_table_name(symbol: str) -> str:
    clean = symbol.upper().replace(".", "_")
    if not re.fullmatch(r"[A-Z0-9_]+", clean):
        raise ValueError(f"Invalid symbol: {symbol}")
    return f"STK{clean}"


class MarketDataStore:
    def __init__(
        self,
        price_db: DBConfig,
        options_db: DBConfig,
        tech_db: Optional[DBConfig] = None,
    ) -> None:
        self.price_engine = self._build_engine(price_db)
        self.options_engine = self._build_engine(options_db)
        self.tech_engine = self._build_engine(tech_db) if tech_db else None

    @staticmethod
    def _build_engine(cfg: DBConfig):
        from DB import open_sql_connection

        return open_sql_connection(
            ip=cfg.host,
            user=cfg.user,
            passwd=cfg.password,
            port=cfg.port,
            db=cfg.db,
        )

    def list_symbols(self, max_symbols: Optional[int] = None) -> List[str]:
        q = "SHOW TABLES LIKE 'STK%'"
        with self.price_engine.connect() as conn:
            rows = conn.execute(text(q)).fetchall()
        symbols = []
        for row in rows:
            tbl = row[0]
            if tbl.startswith("STK"):
                symbols.append(tbl[3:].replace("_", "."))
        symbols = sorted(symbols)
        if max_symbols is not None:
            return symbols[:max_symbols]
        return symbols

    def fetch_price_history(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        table = to_table_name(symbol)
        clauses = []
        params: Dict[str, str] = {}
        if start:
            clauses.append("Date >= :start")
            params["start"] = start
        if end:
            clauses.append("Date <= :end")
            params["end"] = end

        where = ""
        if clauses:
            where = " WHERE " + " AND ".join(clauses)

        query = (
            f"SELECT Date, `Open`, `High`, `Low`, `Close`, `Adj Close`, `Volume` "
            f"FROM {table}{where} ORDER BY Date ASC"
        )
        df = pd.read_sql_query(text(query), self.price_engine, params=params)
        if df.empty:
            return df

        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.dropna(subset=["High", "Low", "Adj Close", "Volume"])
        return df

    def fetch_option_candidates(
        self,
        symbol: str,
        trade_date: pd.Timestamp,
        option_type: str,
        spot_price: float,
        max_dte_days: int,
        dte_window_days: int,
    ) -> pd.DataFrame:
        table = to_table_name(symbol)
        max_dte_days = min(max_dte_days, 60)
        min_dte_days = max(1, max_dte_days - dte_window_days)
        min_exp = (trade_date + timedelta(days=min_dte_days)).date()
        max_exp = (trade_date + timedelta(days=max_dte_days)).date()
        query = text(
            f"""
            SELECT contractID, expiration, strike, mark, date
            FROM {table}
            WHERE date = :trade_date
              AND type = :otype
              AND mark IS NOT NULL
              AND mark > 0
              AND expiration BETWEEN :min_exp AND :max_exp
            """
        )
        params = {
            "trade_date": trade_date.date(),
            "otype": option_type,
            "min_exp": min_exp,
            "max_exp": max_exp,
        }
        df = pd.read_sql_query(query, self.options_engine, params=params)
        if df.empty:
            return df

        df["expiration"] = pd.to_datetime(df["expiration"])
        df["date"] = pd.to_datetime(df["date"])
        df["strike"] = pd.to_numeric(df["strike"], errors="coerce")
        df["mark"] = pd.to_numeric(df["mark"], errors="coerce")
        df = df.dropna(subset=["strike", "mark", "expiration"])

        target_exp = trade_date + timedelta(days=max_dte_days)
        df["expiry_gap"] = (df["expiration"] - target_exp).abs().dt.days
        df["moneyness_gap"] = (df["strike"] - spot_price).abs()
        df = df.sort_values(["expiry_gap", "moneyness_gap", "mark"])  # stable, deterministic choice
        return df

    def fetch_tech_params(self, symbol: str) -> pd.DataFrame:
        if self.tech_engine is None:
            return pd.DataFrame()

        table = to_table_name(symbol)
        try:
            table_exists = inspect(self.tech_engine).has_table(table)
            if not table_exists:
                return pd.DataFrame()

            query = text(
                f"""
                SELECT Date, Sequence, PSAR
                FROM {table}
                ORDER BY Date ASC
                """
            )
            tech_df = pd.read_sql_query(query, self.tech_engine)
        except Exception:
            return pd.DataFrame()

        if tech_df.empty:
            return tech_df

        tech_df["Date"] = pd.to_datetime(tech_df["Date"], errors="coerce")
        tech_df["Sequence"] = pd.to_numeric(tech_df["Sequence"], errors="coerce")
        tech_df["PSAR"] = pd.to_numeric(tech_df["PSAR"], errors="coerce")
        tech_df = tech_df.dropna(subset=["Date", "Sequence"])  # PSAR can still be missing on some rows
        if tech_df.empty:
            return tech_df
        return tech_df.set_index("Date").sort_index()

    def fetch_contract_mark_on_or_after(
        self,
        symbol: str,
        contract_id: str,
        start_date: pd.Timestamp,
    ) -> Optional[Tuple[pd.Timestamp, float]]:
        table = to_table_name(symbol)
        query = text(
            f"""
            SELECT date, mark
            FROM {table}
            WHERE contractID = :cid
              AND date >= :start_date
              AND mark IS NOT NULL
              AND mark > 0
            ORDER BY date ASC
            LIMIT 1
            """
        )
        with self.options_engine.connect() as conn:
            row = conn.execute(
                query,
                {
                    "cid": contract_id,
                    "start_date": start_date.date(),
                },
            ).fetchone()
        if not row:
            return None
        return pd.to_datetime(row[0]), float(row[1])


FEATURE_COLUMNS = [
    "psar_trend",
    "psar_trend_days",
    "psar_duration_ratio",
    "psar_current_trend_return",
    "psar_previous_trend_days",
    "psar_previous_trend_return",
    "psar_avg_long_duration",
    "psar_avg_short_duration",
    "psar_avg_long_return",
    "psar_avg_short_return",
    "psar_trend_return_vs_avg",
    "rsi",
    "rsi_60_day_min",
    "rsi_60_day_max",
    "rsi_from_min_norm",
    "rsi_from_max_norm",
    "rsi_velocity_3",
    "rsi_acceleration",
    "rsi_rebound_from_60d_min",
    "rsi_fade_from_60d_max",
    "ret_1d",
    "ret_5d",
    "ret_20d",
    "price_velocity_5",
    "price_acceleration",
    "atr_pct",
    "vol_zscore_20",
    "volume_change_5d",
    "volume_acceleration",
    "obv_slope_5d",
    "volume_price_pressure_5",
]

def _add_segment_features(
    out: pd.DataFrame,
    close: pd.Series,
    trend: pd.Series,
    trend_days_abs: pd.Series,
    segment_id: pd.Series,
) -> pd.DataFrame:
    segment_first_close = close.groupby(segment_id).transform("first")
    segment_last_close = close.groupby(segment_id).transform("last")
    current_segment_return = segment_last_close / segment_first_close - 1.0

    segment_meta = pd.DataFrame(
        {
            "segment_id": segment_id,
            "trend": trend,
            "length": trend_days_abs.groupby(segment_id).transform("max"),
            "return": current_segment_return,
        },
        index=close.index,
    )
    segment_meta = segment_meta.loc[trend.notna()]
    if segment_meta.empty:
        return out

    segment_meta = segment_meta.loc[~segment_meta["segment_id"].duplicated()].copy()
    segment_meta["avg_len_side"] = np.nan
    segment_meta["avg_return_side"] = np.nan
    for side in [1, -1]:
        mask = segment_meta["trend"] == side
        side_lengths = segment_meta.loc[mask, "length"]
        side_returns = segment_meta.loc[mask, "return"]
        segment_meta.loc[mask, "avg_len_side"] = side_lengths.expanding().mean().shift(1)
        segment_meta.loc[mask, "avg_return_side"] = side_returns.expanding().mean().shift(1)

    fallback_len = segment_meta["length"].expanding().mean().clip(lower=1)
    fallback_return = segment_meta["return"].expanding().mean()
    segment_meta["avg_len_side"] = segment_meta["avg_len_side"].fillna(fallback_len)
    segment_meta["avg_return_side"] = segment_meta["avg_return_side"].fillna(fallback_return)
    segment_meta["prev_length"] = segment_meta["length"].shift(1)
    segment_meta["prev_return"] = segment_meta["return"].shift(1)

    meta_by_segment = segment_meta.set_index("segment_id")
    out["psar_duration_ratio"] = (
        trend_days_abs / segment_id.map(meta_by_segment["avg_len_side"]).replace(0, np.nan)
    ).clip(lower=0)
    out["psar_current_trend_return"] = close / segment_first_close - 1.0
    out["psar_previous_trend_days"] = segment_id.map(meta_by_segment["prev_length"])
    out["psar_previous_trend_return"] = segment_id.map(meta_by_segment["prev_return"])
    out["psar_trend_return_vs_avg"] = (
        out["psar_current_trend_return"] - segment_id.map(meta_by_segment["avg_return_side"])
    )

    long_meta = segment_meta[segment_meta["trend"] == 1].set_index("segment_id")
    short_meta = segment_meta[segment_meta["trend"] == -1].set_index("segment_id")
    out["psar_avg_long_duration"] = segment_id.map(long_meta["avg_len_side"]).ffill()
    out["psar_avg_short_duration"] = segment_id.map(short_meta["avg_len_side"]).ffill()
    out["psar_avg_long_return"] = segment_id.map(long_meta["avg_return_side"]).ffill()
    out["psar_avg_short_return"] = segment_id.map(short_meta["avg_return_side"]).ffill()
    return out


def _adjusted_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    factor = (
        df["Adj Close"].astype(float) / df["Close"].astype(float).replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan)
    adjusted = pd.DataFrame(index=df.index)
    adjusted["Open"] = df["Open"].astype(float) * factor
    adjusted["High"] = df["High"].astype(float) * factor
    adjusted["Low"] = df["Low"].astype(float) * factor
    adjusted["Close"] = df["Adj Close"].astype(float)
    return adjusted


def _compute_psar_state(df: pd.DataFrame) -> pd.DataFrame:
    from common import webull_psar

    adjusted = _adjusted_ohlc(df)
    sar, direction = webull_psar(
        adjusted["High"],
        adjusted["Low"],
        adjusted["Close"],
        acceleration=0.02,
        maximum=0.2,
        return_trend=True,
    )
    trend_arr = np.where(direction == 1, 1, -1).astype(float)
    trend = pd.Series(trend_arr, index=df.index)

    switch = trend.ne(trend.shift(1)).fillna(True)
    segment_id = switch.cumsum()
    trend_days_abs = df.groupby(segment_id).cumcount() + 1
    trend_days_signed = trend_days_abs * trend

    out = pd.DataFrame(index=df.index)
    out["psar_trend"] = trend
    out["psar_trend_days"] = trend_days_signed
    return _add_segment_features(out, df["Adj Close"].astype(float), trend, trend_days_abs, segment_id)


def _psar_state_from_tech_params(price_df: pd.DataFrame, tech_df: pd.DataFrame) -> pd.DataFrame:
    merged = price_df[["Adj Close"]].join(tech_df[["Sequence"]], how="left")
    merged["Sequence"] = pd.to_numeric(merged["Sequence"], errors="coerce")
    seq = merged["Sequence"]

    trend = pd.Series(np.where(seq >= 0, 1, -1), index=merged.index)
    trend = trend.where(seq.notna(), np.nan)
    trend_days_signed = seq
    trend_days_abs = seq.abs()

    switch = trend.ne(trend.shift(1)).fillna(True)
    segment_id = switch.cumsum()
    out = pd.DataFrame(index=price_df.index)
    out["psar_trend"] = trend
    out["psar_trend_days"] = trend_days_signed
    return _add_segment_features(out, merged["Adj Close"].astype(float), trend, trend_days_abs, segment_id)


def build_feature_frame(
    price_df: pd.DataFrame,
    cfg: StrategyConfig,
    tech_psar_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    df = price_df.copy()
    close = df["Adj Close"].astype(float)
    adjusted = _adjusted_ohlc(df)

    # Recompute PSAR from split-adjusted OHLC. Stored tech sequences may have
    # been produced from raw OHLC, which creates false trend flips around splits.
    psar_state = _compute_psar_state(df)

    rsi = pd.Series(talib.RSI(close.values, timeperiod=cfg.rsi_period), index=df.index)
    rsi_min = rsi.rolling(cfg.rsi_window).min()
    rsi_max = rsi.rolling(cfg.rsi_window).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)

    ret_1d = close.pct_change(1)
    ret_5d = close.pct_change(5)
    ret_20d = close.pct_change(20)

    atr = pd.Series(
        talib.ATR(adjusted["High"].values, adjusted["Low"].values, close.values, timeperiod=14),
        index=df.index,
    )
    atr_pct = atr / close

    vol = df["Volume"].astype(float)
    vol_ma20 = vol.rolling(20).mean()
    vol_std20 = vol.rolling(20).std()
    vol_z = (vol - vol_ma20) / vol_std20.replace(0, np.nan)

    obv = pd.Series(talib.OBV(close.values, vol.values), index=df.index)
    obv_slope_5d = obv.diff(5) / 5.0

    out = pd.DataFrame(index=df.index)
    out["Adj Close"] = close
    out["Volume"] = vol
    out["psar_trend"] = psar_state["psar_trend"]
    out["psar_trend_days"] = psar_state["psar_trend_days"]
    out["psar_duration_ratio"] = psar_state["psar_duration_ratio"]
    out["psar_current_trend_return"] = psar_state["psar_current_trend_return"]
    out["psar_previous_trend_days"] = psar_state["psar_previous_trend_days"]
    out["psar_previous_trend_return"] = psar_state["psar_previous_trend_return"]
    out["psar_avg_long_duration"] = psar_state["psar_avg_long_duration"]
    out["psar_avg_short_duration"] = psar_state["psar_avg_short_duration"]
    out["psar_avg_long_return"] = psar_state["psar_avg_long_return"]
    out["psar_avg_short_return"] = psar_state["psar_avg_short_return"]
    out["psar_trend_return_vs_avg"] = psar_state["psar_trend_return_vs_avg"]

    out["rsi"] = rsi
    out["rsi_60_day_min"] = rsi_min
    out["rsi_60_day_max"] = rsi_max
    out["rsi_from_min_norm"] = (rsi - rsi_min) / rsi_range
    out["rsi_from_max_norm"] = (rsi_max - rsi) / rsi_range
    out["rsi_velocity_3"] = rsi.diff(3) / 3.0
    out["rsi_acceleration"] = out["rsi_velocity_3"].diff(2) / 2.0
    out["rsi_rebound_from_60d_min"] = rsi - rsi_min
    out["rsi_fade_from_60d_max"] = rsi_max - rsi

    out["ret_1d"] = ret_1d
    out["ret_5d"] = ret_5d
    out["ret_20d"] = ret_20d
    out["price_velocity_5"] = ret_5d / 5.0
    out["price_acceleration"] = out["price_velocity_5"] - out["price_velocity_5"].shift(5)
    out["atr_pct"] = atr_pct
    out["vol_zscore_20"] = vol_z
    out["volume_change_5d"] = vol.pct_change(5)
    out["volume_acceleration"] = out["volume_change_5d"] - out["volume_change_5d"].shift(5)
    out["obv_slope_5d"] = obv_slope_5d
    out["volume_price_pressure_5"] = ret_5d * vol_z

    return out


def attach_labels(feature_df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    df = feature_df.copy()
    future_return = df["Adj Close"].shift(-cfg.lookahead_days) / df["Adj Close"] - 1.0
    df["future_return"] = future_return

    signal = pd.Series(ACTION_HOLD, index=df.index, dtype="int64")

    buy_call_cond = (
        (df["psar_trend"] < 0)
        & (df["rsi_from_min_norm"] <= cfg.rsi_proximity)
        & (future_return >= cfg.buy_forward_return)
    )

    buy_put_cond = (
        (df["psar_trend"] > 0)
        & (df["rsi_from_max_norm"] <= cfg.rsi_proximity)
        & (future_return <= -cfg.sell_forward_return)
    )

    signal.loc[buy_call_cond] = ACTION_BUY_CALL
    signal.loc[buy_put_cond] = ACTION_BUY_PUT

    df["signal"] = signal
    df["sample_weight"] = 1.0 + (df["future_return"].abs().fillna(0) * 8.0)
    return df


def prepare_symbol_dataset(
    store: MarketDataStore,
    symbol: str,
    strategy_cfg: StrategyConfig,
    start: Optional[str],
    end: Optional[str],
) -> pd.DataFrame:
    price_df = store.fetch_price_history(symbol=symbol, start=start, end=end)
    if price_df.empty or len(price_df) < 260:
        return pd.DataFrame()

    tech_psar_df = store.fetch_tech_params(symbol)
    feature_df = build_feature_frame(price_df, strategy_cfg, tech_psar_df=tech_psar_df)
    model_df = attach_labels(feature_df, strategy_cfg)
    model_df["Symbol"] = symbol
    model_df["Date"] = model_df.index
    model_df.index.name = None
    return model_df


def train_classifier(df: pd.DataFrame, cfg: TrainConfig):
    clean_df = df.dropna(subset=FEATURE_COLUMNS + ["signal", "Date"]).copy()
    if clean_df.empty:
        raise ValueError("No rows left after dropping NA from features and labels")

    cutoff = clean_df["Date"].quantile(0.8)
    train_df = clean_df[clean_df["Date"] <= cutoff].copy()
    test_df = clean_df[clean_df["Date"] > cutoff].copy()

    if train_df.empty or test_df.empty:
        raise ValueError("Unable to split train/test chronologically; adjust date range")

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["signal"].astype(int)
    w_train = train_df["sample_weight"].astype(float)

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["signal"].astype(int)

    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=cfg.n_estimators,
                    max_depth=cfg.max_depth,
                    min_samples_leaf=cfg.min_samples_leaf,
                    class_weight="balanced_subsample",
                    random_state=cfg.random_state,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(X_train, y_train, clf__sample_weight=w_train)

    pred = model.predict(X_test)
    report = classification_report(
        y_test,
        pred,
        labels=[ACTION_HOLD, ACTION_BUY_CALL, ACTION_BUY_PUT],
        target_names=[ACTION_NAME[i] for i in [ACTION_HOLD, ACTION_BUY_CALL, ACTION_BUY_PUT]],
        zero_division=0,
        output_dict=False,
    )
    matrix = confusion_matrix(y_test, pred, labels=[ACTION_HOLD, ACTION_BUY_CALL, ACTION_BUY_PUT])

    return model, train_df, test_df, report, matrix


def infer_actions(model: Pipeline, symbol_df: pd.DataFrame) -> pd.DataFrame:
    df = symbol_df.dropna(subset=FEATURE_COLUMNS).copy()
    if df.empty:
        return df

    pred = model.predict(df[FEATURE_COLUMNS])
    proba = model.predict_proba(df[FEATURE_COLUMNS])
    df["pred_signal"] = pred
    df["pred_signal_name"] = [ACTION_NAME[int(v)] for v in pred]
    df["pred_confidence"] = proba.max(axis=1)
    return df


def run_leaps_backtest(
    store: MarketDataStore,
    symbol: str,
    action_df: pd.DataFrame,
    cfg: StrategyConfig,
) -> pd.DataFrame:
    if action_df.empty:
        return pd.DataFrame()

    position = None
    trades: List[Dict[str, object]] = []

    for idx, row in action_df.iterrows():
        trade_date = pd.to_datetime(idx)
        close_price = float(row["Adj Close"])
        signal = int(row["pred_signal"])

        if position is None:
            if signal in (ACTION_BUY_CALL, ACTION_BUY_PUT):
                option_type = "CALL" if signal == ACTION_BUY_CALL else "PUT"
                candidates = store.fetch_option_candidates(
                    symbol=symbol,
                    trade_date=trade_date,
                    option_type=option_type,
                    spot_price=close_price,
                    max_dte_days=cfg.max_dte_days,
                    dte_window_days=cfg.dte_window_days,
                )
                if candidates.empty:
                    continue

                best = candidates.iloc[0]
                position = {
                    "side": option_type,
                    "contract_id": best["contractID"],
                    "entry_date": trade_date,
                    "entry_price": float(best["mark"]),
                    "entry_signal": ACTION_NAME[signal],
                }
            continue

        close_call = position["side"] == "CALL" and signal == ACTION_BUY_PUT
        close_put = position["side"] == "PUT" and signal == ACTION_BUY_CALL
        if not (close_call or close_put):
            continue

        exit_mark = store.fetch_contract_mark_on_or_after(
            symbol=symbol,
            contract_id=position["contract_id"],
            start_date=trade_date,
        )
        if exit_mark is None:
            continue

        exit_date, exit_price = exit_mark
        entry_price = float(position["entry_price"])
        pnl = (exit_price - entry_price) / entry_price

        trades.append(
            {
                "Symbol": symbol,
                "Side": position["side"],
                "ContractID": position["contract_id"],
                "EntryDate": position["entry_date"],
                "ExitDate": exit_date,
                "EntryPrice": entry_price,
                "ExitPrice": exit_price,
                "Return": pnl,
                "EntrySignal": position["entry_signal"],
                "ExitSignal": ACTION_NAME[signal],
            }
        )
        position = None

    if position is not None:
        final_date = pd.to_datetime(action_df.index[-1])
        exit_mark = store.fetch_contract_mark_on_or_after(
            symbol=symbol,
            contract_id=position["contract_id"],
            start_date=final_date,
        )
        if exit_mark is not None:
            exit_date, exit_price = exit_mark
            entry_price = float(position["entry_price"])
            pnl = (exit_price - entry_price) / entry_price
            trades.append(
                {
                    "Symbol": symbol,
                    "Side": position["side"],
                    "ContractID": position["contract_id"],
                    "EntryDate": position["entry_date"],
                    "ExitDate": exit_date,
                    "EntryPrice": entry_price,
                    "ExitPrice": exit_price,
                    "Return": pnl,
                    "EntrySignal": position["entry_signal"],
                    "ExitSignal": "FORCED_FINAL_EXIT",
                }
            )

    if not trades:
        return pd.DataFrame()
    return pd.DataFrame(trades)


def save_symbol_features(df: pd.DataFrame, output_dir: Path, symbol: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"STK{symbol.replace('.', '_')}_features.csv"
    df.to_csv(out_file, index=False)


def summarize_trade_results(trades_df: pd.DataFrame) -> Dict[str, float]:
    if trades_df.empty:
        return {
            "num_trades": 0,
            "win_rate": 0.0,
            "avg_return": 0.0,
            "total_return_compounded": 0.0,
        }

    wins = (trades_df["Return"] > 0).sum()
    num = len(trades_df)
    compounded = float((1.0 + trades_df["Return"]).prod() - 1.0)

    return {
        "num_trades": float(num),
        "win_rate": float(wins / num),
        "avg_return": float(trades_df["Return"].mean()),
        "total_return_compounded": compounded,
    }


def run_pipeline(
    symbols: Optional[List[str]] = None,
    max_symbols: int = 200,
    start: Optional[str] = None,
    end: Optional[str] = None,
    output_dir: str = "model_outputs",
    strategy_cfg: Optional[StrategyConfig] = None,
    train_cfg: Optional[TrainConfig] = None,
) -> None:
    price_db = DBConfig(host="10.89.45.241", db="US_Stocks")
    options_db = DBConfig(host="10.89.45.31", db="US_Stocks_Options")
    tech_db = DBConfig(host="10.89.45.241", db="US_Tech_Params")

    strategy_cfg = strategy_cfg or StrategyConfig()
    train_cfg = train_cfg or TrainConfig()
    store = MarketDataStore(price_db=price_db, options_db=options_db, tech_db=tech_db)

    if symbols is None or len(symbols) == 0:
        symbols = store.list_symbols(max_symbols=max_symbols)

    all_rows = []
    per_symbol = {}
    for sym in symbols:
        try:
            sdf = prepare_symbol_dataset(store, sym, strategy_cfg, start, end)
            if sdf.empty:
                continue
            all_rows.append(sdf)
            per_symbol[sym] = sdf
        except Exception as exc:
            print(f"Skipping {sym}: {exc}")

    if not all_rows:
        raise RuntimeError("No symbol dataset was generated. Check DB connectivity and date range.")

    dataset = pd.concat(all_rows, axis=0).sort_values("Date")

    model, train_df, test_df, report, matrix = train_classifier(dataset, train_cfg)

    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "features").mkdir(parents=True, exist_ok=True)
    (out_root / "signals").mkdir(parents=True, exist_ok=True)
    (out_root / "trades").mkdir(parents=True, exist_ok=True)

    dataset.to_csv(out_root / "training_dataset.csv", index=False)
    train_df.to_csv(out_root / "train_split.csv", index=False)
    test_df.to_csv(out_root / "test_split.csv", index=False)

    with open(out_root / "classification_report.txt", "w", encoding="utf-8") as fp:
        fp.write(report)
        fp.write("\n\nConfusion Matrix (rows=true, cols=pred):\n")
        fp.write(np.array2string(matrix))

    print("=== Classification Report ===")
    print(report)
    print("Confusion Matrix:")
    print(matrix)

    all_trades = []
    summary_rows = []
    for sym, sdf in per_symbol.items():
        action_df = infer_actions(model, sdf)
        trades_df = run_leaps_backtest(store, sym, action_df, strategy_cfg)

        save_symbol_features(sdf.reset_index(drop=True), out_root / "features", sym)
        action_df.to_csv(out_root / "signals" / f"{sym}_signals.csv", index=False)

        if not trades_df.empty:
            trades_df.to_csv(out_root / "trades" / f"{sym}_trades.csv", index=False)
            all_trades.append(trades_df)

        metrics = summarize_trade_results(trades_df)
        metrics["Symbol"] = sym
        summary_rows.append(metrics)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_root / "backtest_summary.csv", index=False)

    if all_trades:
        trades = pd.concat(all_trades, axis=0)
        trades.to_csv(out_root / "all_trades.csv", index=False)
        print("=== Backtest Aggregate ===")
        print(summarize_trade_results(trades))
    else:
        print("No option trades were generated with current signal thresholds.")

    print(f"Artifacts saved at: {out_root.resolve()}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PSAR + RSI + pace ML model with options backtest"
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="",
        help="Comma-separated symbols, e.g. AAPL,NVDA,MSFT",
    )
    parser.add_argument("--max-symbols", type=int, default=200)
    parser.add_argument("--start", type=str, default=None, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, default=None, help="End date YYYY-MM-DD")
    parser.add_argument("--output-dir", type=str, default="model_outputs")
    parser.add_argument("--rsi-period", type=int, default=14)
    parser.add_argument("--rsi-window", type=int, default=60)
    parser.add_argument("--lookahead-days", type=int, default=20)
    parser.add_argument("--rsi-proximity", type=float, default=0.15)
    parser.add_argument("--buy-forward-return", type=float, default=0.08)
    parser.add_argument("--sell-forward-return", type=float, default=0.08)
    parser.add_argument("--max-dte-days", type=int, default=60)
    parser.add_argument("--dte-window-days", type=int, default=45)
    parser.add_argument("--n-estimators", type=int, default=400)
    parser.add_argument("--max-depth", type=int, default=10)
    parser.add_argument("--min-samples-leaf", type=int, default=20)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()] if args.symbols else None
    strategy_cfg = StrategyConfig(
        rsi_period=args.rsi_period,
        rsi_window=args.rsi_window,
        lookahead_days=args.lookahead_days,
        rsi_proximity=args.rsi_proximity,
        buy_forward_return=args.buy_forward_return,
        sell_forward_return=args.sell_forward_return,
        max_dte_days=args.max_dte_days,
        dte_window_days=args.dte_window_days,
    )
    train_cfg = TrainConfig(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        min_samples_leaf=args.min_samples_leaf,
        random_state=args.random_state,
    )
    run_pipeline(
        symbols=symbols,
        max_symbols=args.max_symbols,
        start=args.start,
        end=args.end,
        output_dir=args.output_dir,
        strategy_cfg=strategy_cfg,
        train_cfg=train_cfg,
    )


if __name__ == "__main__":
    main()
