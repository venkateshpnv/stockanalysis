import pandas as pd
from sqlalchemy import create_engine
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report

# 📦 Load earnings history and compute rolling features
#def compute_earnings_history_features(df_history):
#    df_history['reportDate'] = pd.to_datetime(df_history['reportDate'])
#    df_history = df_history.sort_values(['Symbol', 'reportDate'])
#
#    grouped = df_history.groupby('Symbol')
#    df_history['last_price_change'] = grouped['price_change'].shift(1)
#    df_history['last_surprise'] = grouped['surprise'].shift(1)
#    df_history['avg_price_change_last_3'] = grouped['price_change'].shift(1).rolling(3).mean().reset_index(drop=True)
#    df_history['median_price_change_2y'] = grouped['price_change'].shift(1).rolling(8).median().reset_index(drop=True)
#
#    return df_history

def compute_earnings_history_features(df_history):
    df_history['reportDate'] = pd.to_datetime(df_history['reportDate'])
    df_history = df_history.sort_values(['Symbol', 'reportDate'])

    grouped = df_history.groupby('Symbol')

    # Rolling price change features
    df_history['last_price_change'] = grouped['price_change'].shift(1)
    df_history['last_surprise'] = grouped['surprise'].shift(1)
    df_history['avg_price_change_last_3'] = grouped['price_change'].shift(1).rolling(3).mean().reset_index(drop=True)
    df_history['median_price_change_2y'] = grouped['price_change'].shift(1).rolling(8).median().reset_index(drop=True)
    df_history['std_price_change_last_3'] = grouped['price_change'].shift(1).rolling(3).std().reset_index(drop=True)
    df_history['std_price_change_2y'] = grouped['price_change'].shift(1).rolling(8).std().reset_index(drop=True)

    # Seasonality
    df_history['quarter'] = df_history['reportDate'].dt.quarter
    df_history['is_q1'] = (df_history['quarter'] == 1).astype(int)
    df_history['is_q2'] = (df_history['quarter'] == 2).astype(int)
    df_history['is_q3'] = (df_history['quarter'] == 3).astype(int)
    df_history['is_q4'] = (df_history['quarter'] == 4).astype(int)

    return df_history


# 🔌 Load and merge training data
def load_training_data(sql_uri):
    engine = create_engine(sql_uri)

    # Load base training data
    df_train = pd.read_sql("SELECT * FROM Nasdaq_Earnings_Options", engine)
    df_train['reportDate'] = pd.to_datetime(df_train['reportDate'])

    # Load earnings history
    df_history = pd.read_sql("SELECT Symbol, reportDate, price_change, surprise FROM Nasdaq_Earnings_History", engine)
    df_history = compute_earnings_history_features(df_history)

    # Merge historical features
    df = pd.merge(
        df_train,
        df_history[['Symbol', 'reportDate', 'last_price_change', 'last_surprise',
                    'avg_price_change_last_3', 'median_price_change_2y']],
        on=['Symbol', 'reportDate'],
        how='left'
    )

    # Define target
    df['target'] = (df['profit_on_one_contract'] > 0).astype(int)

    return df

# 🧱 Build pipeline
def build_pipeline(numeric_features):
    num_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    preprocessor = ColumnTransformer([
        ('num', num_transformer, numeric_features)
    ])

    clf = Pipeline([
        ('prep', preprocessor),
        ('model', RandomForestClassifier(
            n_estimators=200,
            max_depth=7,
            random_state=42,
            n_jobs=-1
        ))
    ])

    return clf

# 🚀 Train and evaluate
def main():
    SQL_URI = "mysql+pymysql://user:pass@localhost/US_Stocks_Fin"
    df = load_training_data(SQL_URI)

    FEATURES = [
        'surprise', 'epsForecast', 'noOfEsts', 'marketCap',
        'price_change', 'implied_volatility', 'delta', 'theta', 'vega',
        'last_price_change', 'last_surprise',
        'avg_price_change_last_3', 'median_price_change_2y'
    ]

    df = df.dropna(subset=['target'])  # Ensure target is present
    X = df[FEATURES]
    y = df['target']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipeline = build_pipeline(FEATURES)
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)

    print(f"\nHold-out ROC AUC: {auc:.3f}")
    print(classification_report(y_test, y_pred, digits=3))

if __name__ == "__main__":
    main()import pandas as pd
from sqlalchemy import create_engine
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report

# 📦 Load earnings history and compute rolling features
def compute_earnings_history_features(df_history):
    df_history['reportDate'] = pd.to_datetime(df_history['reportDate'])
    df_history = df_history.sort_values(['Symbol', 'reportDate'])

    grouped = df_history.groupby('Symbol')
    df_history['last_price_change'] = grouped['price_change'].shift(1)
    df_history['last_surprise'] = grouped['surprise'].shift(1)
    df_history['avg_price_change_last_3'] = grouped['price_change'].shift(1).rolling(3).mean().reset_index(drop=True)
    df_history['median_price_change_2y'] = grouped['price_change'].shift(1).rolling(8).median().reset_index(drop=True)

    return df_history

# 🔌 Load and merge training data
def load_training_data(sql_uri):
    engine = create_engine(sql_uri)

    # Load base training data
    df_train = pd.read_sql("SELECT * FROM Nasdaq_Earnings_Options", engine)
    df_train['reportDate'] = pd.to_datetime(df_train['reportDate'])

    # Load earnings history
    df_history = pd.read_sql("SELECT Symbol, reportDate, price_change, surprise FROM Nasdaq_Earnings_History", engine)
    df_history = compute_earnings_history_features(df_history)

    # Merge historical features
    df = pd.merge(
        df_train,
        df_history[['Symbol', 'reportDate', 'last_price_change', 'last_surprise',
                    'avg_price_change_last_3', 'median_price_change_2y']],
        on=['Symbol', 'reportDate'],
        how='left'
    )

    # Define target
    df['target'] = (df['profit_on_one_contract'] > 0).astype(int)

    return df

# 🧱 Build pipeline
def build_pipeline(numeric_features):
    num_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    preprocessor = ColumnTransformer([
        ('num', num_transformer, numeric_features)
    ])

    clf = Pipeline([
        ('prep', preprocessor),
        ('model', RandomForestClassifier(
            n_estimators=200,
            max_depth=7,
            random_state=42,
            n_jobs=-1
        ))
    ])

    return clf

# 🚀 Train and evaluate
def main():
    SQL_URI = "mysql+pymysql://user:pass@localhost/US_Stocks_Fin"
    df = load_training_data(SQL_URI)

    FEATURES = [
        'surprise', 'epsForecast', 'noOfEsts', 'marketCap',
        'price_change', 'implied_volatility', 'delta', 'theta', 'vega',
        'last_price_change', 'last_surprise',
        'avg_price_change_last_3', 'median_price_change_2y'
    ]

    df = df.dropna(subset=['target'])  # Ensure target is present
    X = df[FEATURES]
    y = df['target']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    pipeline = build_pipeline(FEATURES)
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)

    print(f"\nHold-out ROC AUC: {auc:.3f}")
    print(classification_report(y_test, y_pred, digits=3))

if __name__ == "__main__":
    main()
