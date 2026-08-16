import argparse
import copy
import sys
from datetime import datetime as dt

import pandas as pd
from dateutil.relativedelta import relativedelta

import DB


COUNTRY = "US"
MONGO_DB = "Stocks"
TECH_PARAMS_DB = "US_Tech_Params"


def get_listed_stock_query(symbol=None):
    query = {
        "$and": [
            {"General.IsDelisted": False},
            {"General.Type": "Common Stock"},
            {
                "$or": [
                    {"General.Exchange": {"$in": DB.major_exchanges}},
                    {
                        "$and": [
                            {"General.Exchange": {"$nin": DB.major_exchanges}},
                            {"bscs.tracking": {"$exists": True}},
                        ]
                    },
                ]
            },
        ]
    }
    if symbol:
        query["$and"].append({"bscs.symbol": symbol})
    return query


def get_listed_stocks(limit=None):
    client = DB.open_db_client()
    try:
        collection = client[MONGO_DB].US_Stocks
        cursor = (
            collection.find(get_listed_stock_query(), no_cursor_timeout=True)
            .batch_size(100)
            .sort([["failcount.mysql_price_failcount", 1]])
            .allow_disk_use(True)
            .sort([["sno", 1]])
            .allow_disk_use(True)
        )
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)
    finally:
        DB.close_db_client(client)


def get_listed_stock(symbol):
    client = DB.open_db_client()
    try:
        collection = client[MONGO_DB].US_Stocks
        return collection.find_one(get_listed_stock_query(symbol))
    finally:
        DB.close_db_client(client)


def find_split_like_day_changes(params_engine, sym, threshold, years, absolute=False):
    table_name = DB.get_symbol_table_name(sym)
    if not table_name or not DB.mysql_exists_table(params_engine, table_name):
        return pd.DataFrame()

    start_date = str((dt.now() - relativedelta(years=years)).date())
    comparator = "ABS(`Day Change`) >= %.7f" if absolute else "`Day Change` <= %.7f"
    threshold_value = abs(threshold) if absolute else -abs(threshold)
    query = (
        "SELECT `Date`, `Day Change` "
        "FROM `{table}` "
        "WHERE `Date` >= '{start_date}' "
        "AND `Day Change` IS NOT NULL "
        "AND {comparator} "
        "ORDER BY `Date`"
    ).format(table=table_name, start_date=start_date, comparator=comparator % threshold_value)

    return DB.read_from_sql(query, params_engine)


def drop_tech_params_table(params_engine, sym):
    table_name = DB.get_symbol_table_name(sym)
    if table_name and DB.mysql_exists_table(params_engine, table_name):
        params_engine.execute("DROP TABLE `{}`".format(table_name))


def repair_stock(params_engine, stk, core, dry_run=False):
    sym = stk.get("bscs", {}).get("symbol")
    name = stk.get("General", {}).get("Name", "")
    if dry_run:
        print(
            "DRY RUN: would drop US_Tech_Params.%s, repopulate prices, and recalculate params for %s %s"
            % (DB.get_symbol_table_name(sym), sym, name)
        )
        return

    drop_tech_params_table(params_engine, sym)
    DB.repopulate_prices(
        COUNTRY,
        sym,
        copy.deepcopy(stk),
        core,
        True,
        False,
        None,
    )


def process_stock(params_engine, stk, index, threshold, years, dry_run=False, absolute=False):
    sym = stk.get("bscs", {}).get("symbol")
    if not sym:
        return False, True

    try:
        matches = find_split_like_day_changes(
            params_engine,
            sym,
            threshold=threshold,
            years=years,
            absolute=absolute,
        )
        if matches.empty:
            return False, False

        print("%d: %s split-like Day Change rows:" % (index, sym))
        print(matches[["Date", "Day Change"]].to_string(index=False))
        repair_stock(params_engine, stk, index % DB.num_cores, dry_run=dry_run)
        return True, False
    except Exception as exc:
        print("%d: %s failed: %s" % (index, sym, str(exc)))
        return False, False


def fix_split_price_data(threshold=0.20, years=5, dry_run=False, symbol=None, limit=None, absolute=False):
    params_engine = DB.open_sql_connection("localhost", "vpetla", "petla123", db=TECH_PARAMS_DB)
    repaired = []
    skipped = 0
    scanned = 0

    try:
        print(
            "Trigger: %s within last %d years"
            % (
                "ABS(Day Change) >= %.2f%%" % (threshold * 100)
                if absolute
                else "Day Change <= -%.2f%%" % (threshold * 100),
                years,
            )
        )

        if symbol:
            stk = get_listed_stock(symbol)
            if not stk:
                print("No listed stock found for symbol: %s" % symbol)
            else:
                scanned = 1
                print("Listed stocks to scan: 1")
                repaired_stock, skipped_stock = process_stock(
                    params_engine,
                    stk,
                    0,
                    threshold=threshold,
                    years=years,
                    dry_run=dry_run,
                    absolute=absolute,
                )
                if repaired_stock:
                    repaired.append(stk["bscs"]["symbol"])
                if skipped_stock:
                    skipped += 1
        else:
            stocks = get_listed_stocks(limit=limit)
            print("Listed stocks to scan: %d" % len(stocks))

            i = 0
            for stk in stocks:
                scanned += 1
                repaired_stock, skipped_stock = process_stock(
                    params_engine,
                    stk,
                    i,
                    threshold=threshold,
                    years=years,
                    dry_run=dry_run,
                    absolute=absolute,
                )
                if repaired_stock:
                    repaired.append(stk["bscs"]["symbol"])
                if skipped_stock:
                    skipped += 1
                i = i + 1

    finally:
        DB.close_sql_connection(params_engine)

    print("Scanned: %d, repaired: %d, skipped: %d" % (scanned, len(repaired), skipped))
    if repaired:
        print("Repaired symbols: %s" % ", ".join(repaired))


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Find currently listed US stocks with split-like Day Change values "
            "in US_Tech_Params, then repull complete price data and recalculate params."
        )
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.20,
        help="Day Change trigger threshold as a decimal. Default: 0.20",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="Number of years to scan. Default: 5",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print matching symbols without changing price/params tables.",
    )
    parser.add_argument(
        "--symbol",
        help="Scan only one symbol, useful for manual testing.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Scan only the first N listed stocks, useful for manual testing.",
    )
    parser.add_argument(
        "--absolute",
        action="store_true",
        help="Trigger on abs(Day Change) >= threshold instead of only drops.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.threshold <= 0:
        print("threshold must be positive")
        sys.exit(1)
    if args.years <= 0:
        print("years must be positive")
        sys.exit(1)

    fix_split_price_data(
        threshold=args.threshold,
        years=args.years,
        dry_run=args.dry_run,
        symbol=args.symbol,
        limit=args.limit,
        absolute=args.absolute,
    )
