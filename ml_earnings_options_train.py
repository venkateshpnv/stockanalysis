# earnings_pipeline_improved.py
import os
import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import RandomizedSearchCV, TimeSeriesSplit
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report, roc_curve, confusion_matrix
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
import joblib
from scipy.stats import randint, uniform

# ---------- Configuration ----------
SQL_URI = "mysql+pymysql://user:pass@localhost/US_Stocks_Fin"
MODEL_OUT_PATH = "./rf_calibrated_pipeline.joblib"
RANDOM_STATE = 42
N_JOBS = -1
RANDOMIZED_SEARCH_N_ITER = 40
TS_SPLITS = 3
TRAIN_QUANTILE = 0.8  # oldest 80% by reportDate -> train, newest 20% -> test
# -----------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def compute_earnings_history_features(df_history):
    """
    Correct per-symbol rolling computations using groupby.apply so group boundaries are respected.
    Assumes df_history has columns: Symbol, reportDate, price_change, surprise
    """
    df = df_history.copy()
    df['reportDate'] = pd.to_datetime(df['reportDate'])
    df = df.sort_values(['Symbol', 'reportDate'])
    grp = df.groupby('Symbol', group_keys=False)

    # Lag features (previous report values)
    df['last_price_change'] = grp['price_change'].apply(lambda s: s.shift(1))
    df['last_surprise'] = grp['surprise'].apply(lambda s: s.shift(1))

    # Rolling features: shift first to exclude current report, then rolling on previous N entries
    df['avg_price_change_last_3'] = grp['price_change'].apply(
        lambda s: s.shift(1).rolling(3, min_periods=1).mean()
    )
    df['median_price_change_2y'] = grp['price_change'].apply(
        lambda s: s.shift(1).rolling(8, min_periods=1).median()
    )
    df['std_price_change_last_3'] = grp['price_change'].apply(
        lambda s: s.shift(1).rolling(3, min_periods=1).std()
    )
    df['std_price_change_2y'] = grp['price_change'].apply(
        lambda s: s.shift(1).rolling(8, min_periods=1).std()
    )

    # Quarter flags
    df['quarter'] = df['reportDate'].dt.quarter
    for q in range(1, 5):
        df[f'is_q{q}'] = (df['quarter'] == q).astype(int)

    return df


def load_training_data(sql_uri):
    """
    Reads main training table and history table, computes history features, merges and returns combined df.
    """
    logging.info("Connecting to database and loading tables...")
    engine = create_engine(sql_uri)

    df_train = pd.read_sql("SELECT * FROM Nasdaq_Earnings_Options", engine)
    df_train['reportDate'] = pd.to_datetime(df_train['reportDate'])

    df_history = pd.read_sql(
        "SELECT Symbol, reportDate, price_change, surprise FROM Nasdaq_Earnings_History",
        engine
    )
    df_history = compute_earnings_history_features(df_history)

    # Merge history features into training rows
    logging.info("Merging history features into training table...")
    merge_cols = [
        'Symbol', 'reportDate',
        'last_price_change', 'last_surprise',
        'avg_price_change_last_3', 'median_price_change_2y',
        'std_price_change_last_3', 'std_price_change_2y',
        'is_q1', 'is_q2', 'is_q3', 'is_q4'
    ]
    df = pd.merge(
        df_train,
        df_history[merge_cols],
        on=['Symbol', 'reportDate'],
        how='left'
    )

    # Target: profitable option trade (binary)
    df['target'] = (df['profit_on_one_contract'] > 0).astype(int)

    return df


def build_pipeline(numeric_features):
    """
    Build a sklearn pipeline with numeric imputation + scaling + RandomForestClassifier.
    The pipeline is used directly in RandomizedSearchCV so hyperparameters for 'model' can be tuned.
    """
    num_transformer = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),  # robust to outliers
        ('scaler', StandardScaler())
    ])

    preprocessor = ColumnTransformer([
        ('num', num_transformer, numeric_features)
    ])

    pipeline = Pipeline([
        ('prep', preprocessor),
        ('model', RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=N_JOBS))
    ])

    return pipeline


def safe_clean_df(df, features, target_col='target'):
    """
    Basic cleaning: drop rows missing target, remove infs, ensure features are numeric.
    """
    logging.info("Cleaning DataFrame: dropping rows without target, removing infinite values...")
    df = df.dropna(subset=[target_col]).copy()

    # Ensure numeric columns are numeric
    for c in features:
        if c not in df.columns:
            raise KeyError(f"Feature column '{c}' not found in dataframe")
        df[c] = pd.to_numeric(df[c], errors='coerce')

    # Replace infinities with NaN (so imputer can handle)
    df.replace([np.inf, -np.inf], np.nan, inplace=True)

    return df


def time_based_train_test_split(df, date_col='reportDate', quantile=TRAIN_QUANTILE):
    """
    Train on older data (<= quantile) and test on newer data (> quantile).
    This is better for time-series/event-driven problems (avoids shuffling leakage).
    """
    cutoff = df[date_col].quantile(quantile)
    train_df = df[df[date_col] <= cutoff].copy()
    test_df = df[df[date_col] > cutoff].copy()
    logging.info(f"Time split cutoff: {cutoff}. Train rows: {len(train_df)}, Test rows: {len(test_df)}")
    return train_df, test_df


def run_hyperparameter_search(pipeline, X_train, y_train):
    """
    RandomizedSearchCV over a sensible RF hyperparameter space using TimeSeriesSplit for CV.
    """

    param_dist = {
        'model__n_estimators': randint(50, 600),
        'model__max_depth': randint(3, 20),
        'model__min_samples_split': randint(2, 10),
        'model__min_samples_leaf': randint(1, 8),
        'model__max_features': ['sqrt', 'log2', None, 0.2, 0.5, 0.8],
        'model__class_weight': [None, 'balanced', 'balanced_subsample']
    }

    tscv = TimeSeriesSplit(n_splits=TS_SPLITS)
    search = RandomizedSearchCV(
        estimator=pipeline,
        param_distributions=param_dist,
        n_iter=RANDOMIZED_SEARCH_N_ITER,
        scoring='roc_auc',
        n_jobs=N_JOBS,
        cv=tscv,
        verbose=2,
        random_state=RANDOM_STATE,
        refit=True
    )

    logging.info("Starting randomized hyperparameter search (time-series CV)...")
    search.fit(X_train, y_train)
    logging.info(f"Best CV score (roc_auc): {search.best_score_:.4f}")
    logging.info(f"Best params: {search.best_params_}")
    return search


def calibrate_classifier(best_pipeline, X_train, y_train):
    """
    Calibrate probabilities of a fitted pipeline using CalibratedClassifierCV.
    We'll use 'sigmoid' calibration (Platt scaling) as default.
    """
    logging.info("Calibrating probabilities with CalibratedClassifierCV...")
    # CalibratedClassifierCV requires an unfitted estimator or 'prefit' estimator.
    # best_pipeline is returned from RandomizedSearchCV with refit=True and is already fitted,
    # so we can use cv='prefit'.
    calibrated = CalibratedClassifierCV(base_estimator=best_pipeline, cv='prefit', method='sigmoid')
    calibrated.fit(X_train, y_train)
    return calibrated


def plot_roc_curve(y_test, y_proba, out_path=None):
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    plt.figure()
    plt.plot(fpr, tpr)  # don't set colors/styles per user instruction
    plt.plot([0, 1], [0, 1], linestyle='--')
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('ROC Curve')
    if out_path:
        plt.savefig(out_path, bbox_inches='tight')
        logging.info(f"Saved ROC curve to {out_path}")
    else:
        plt.show()
    plt.close()


def plot_confusion_matrix(y_test, y_pred, out_path=None):
    cm = confusion_matrix(y_test, y_pred)
    plt.figure()
    plt.imshow(cm, interpolation='nearest', aspect='auto')
    plt.title('Confusion Matrix')
    plt.xlabel('Predicted label')
    plt.ylabel('True label')
    plt.colorbar()
    # annotate counts
    for (i, j), val in np.ndenumerate(cm):
        plt.text(j, i, int(val), ha='center', va='center')
    if out_path:
        plt.savefig(out_path, bbox_inches='tight')
        logging.info(f"Saved confusion matrix to {out_path}")
    else:
        plt.show()
    plt.close()


def main():
    # Features used (all numeric)
    FEATURES = [
        'surprise', 'epsForecast', 'noOfEsts', 'marketCap',
        'price_change', 'implied_volatility', 'delta', 'theta', 'vega',
        'last_price_change', 'last_surprise',
        'avg_price_change_last_3', 'median_price_change_2y',
        'std_price_change_last_3', 'std_price_change_2y',
        'is_q1', 'is_q2', 'is_q3', 'is_q4'
    ]

    # 1) Load & merge
    df = load_training_data(SQL_URI)

    # 2) Basic cleaning; ensure features exist and are numeric
    df = safe_clean_df(df, FEATURES, target_col='target')

    # 3) Time-based split (train on older, test on newer)
    train_df, test_df = time_based_train_test_split(df, date_col='reportDate', quantile=TRAIN_QUANTILE)

    X_train = train_df[FEATURES]
    y_train = train_df['target']
    X_test = test_df[FEATURES]
    y_test = test_df['target']

    # 4) Build pipeline (model hyperparams will be set by RandomizedSearchCV)
    pipeline = build_pipeline(FEATURES)

    # 5) Hyperparameter search (time-series aware)
    search = run_hyperparameter_search(pipeline, X_train, y_train)
    best_pipeline = search.best_estimator_

    # 6) Calibrate probabilities using the fitted best_pipeline
    calibrated_clf = calibrate_classifier(best_pipeline, X_train, y_train)

    # 7) Evaluate on test set
    logging.info("Evaluating on hold-out test set...")
    y_pred = calibrated_clf.predict(X_test)
    # predict_proba returns shape (n_samples, n_classes); positive class probability at index 1
    if hasattr(calibrated_clf, "predict_proba"):
        y_proba = calibrated_clf.predict_proba(X_test)[:, 1]
    else:
        # fallback: use decision_function mapped through logistic if necessary
        y_proba = calibrated_clf.decision_function(X_test)
        # map to [0,1] by min-max (not ideal) - but this branch is unlikely for CalibratedClassifierCV
        y_proba = (y_proba - y_proba.min()) / (y_proba.max() - y_proba.min())

    auc = roc_auc_score(y_test, y_proba)
    logging.info(f"Hold-out ROC AUC: {auc:.4f}")
    print(classification_report(y_test, y_pred, digits=4))

    # 8) Feature importances (RandomForest inside pipeline)
    try:
        rf = best_pipeline.named_steps['model']
        importances = rf.feature_importances_
        feat_imp = sorted(zip(FEATURES, importances), key=lambda x: x[1], reverse=True)
        logging.info("Top feature importances:")
        for f, imp in feat_imp[:20]:
            logging.info(f"  {f}: {imp:.6f}")
    except Exception as e:
        logging.warning(f"Could not extract feature importances from pipeline: {e}")

    # 9) Plots (ROC curve + confusion matrix)
    os.makedirs("plots", exist_ok=True)
    plot_roc_curve(y_test, y_proba, out_path="plots/roc_curve.png")
    plot_confusion_matrix(y_test, y_pred, out_path="plots/confusion_matrix.png")

    # 10) Save final calibrated pipeline to disk
    logging.info(f"Saving calibrated pipeline to {MODEL_OUT_PATH} ...")
    joblib.dump(calibrated_clf, MODEL_OUT_PATH)
    logging.info("Saved model.")

    logging.info("Done.")


if __name__ == "__main__":
    main()

