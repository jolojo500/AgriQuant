import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from xgboost import XGBRegressor
from lightgbm import LGBMRegressor
from etl.transform_config import START_YEAR
from db.queries import read_ml_features, save_training_run

# Minimum quarters needed before we start predicting
# 12 quarters = 3 years of training data minimum
MIN_TRAIN_QUARTERS = 16 #12

MODEL_PATH = "ml/model.pkl"


def prepare_data(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """
    Cleans and prepares the ML dataset for training.
    - Drops rows where target is NaN (last quarter of each ticker)
    - One-hot encodes ticker so the model can distinguish stocks
    - Keeps feature NaNs as-is (XGBoost handles them, OLS/RF get median imputation)
    """
    df = df.dropna(subset=["stock_return_next_q"]).copy()

    # One-hot encode ticker, turns "CTVA" into ticker_CTVA=1, ticker_NTR=0, etc.
    df = pd.get_dummies(df, columns=["ticker"], prefix="ticker")

    # Drop non-feature columns
    drop_cols = ["quarter", "stock_return_next_q"]
    feature_cols = [c for c in df.columns if c not in drop_cols]

    X = df[feature_cols]
    y = df["stock_return_next_q"]

    return X, y


def impute_nans(X_train: pd.DataFrame, X_test: pd.DataFrame) -> tuple:
    """
    Fills NaN values with the median of the training set.
    We compute median on train only — never let test data influence train stats.
    XGBoost doesnt need this but OLS and RF do.
    """
    medians = X_train.median().fillna(0) #fills with 0 if entire column is na, happens for example for stock_return_lag1q in the begining of the train
    return X_train.fillna(medians), X_test.fillna(medians)


def walk_forward_cv(
    X: pd.DataFrame,
    y: pd.Series,
    quarters_col: pd.Series,
    tickers_col: pd.Series,
    model,
    model_name: str,
) -> tuple[float, pd.DataFrame]:
    """
    Walk-forward cross-validation on quarterly data.
    Trains on all past quarters, predicts one quarter at a time.
    Returns (avg_rmse, predictions_df). predictions_df contains genuine
    out-of-sample predictions per (ticker, quarter) — safe to use as
    a historical track record, since each fold only trains on the past.

    Example with 28 quarters, MIN_TRAIN_QUARTERS=12:
      Step 1: train on Q1-Q12, predict Q13
      Step 2: train on Q1-Q13, predict Q14
      ...
      Step 16: train on Q1→Q27, predict Q28
    aka
    For each quarter Q: train on all tickers before Q, predict all tickers at Q.
    """
    unique_quarters = sorted(quarters_col.unique())

    if len(unique_quarters) < MIN_TRAIN_QUARTERS + 1:
        print(f"  Not enough quarters for walk-forward ({len(unique_quarters)} available)")
        return float("inf"), pd.DataFrame()

    errors = []
    fold_predictions = []

    for i in range(MIN_TRAIN_QUARTERS, len(unique_quarters)):
        train_quarters = unique_quarters[:i]     # all quarters before current
        test_quarter  = unique_quarters[i]      # one quarter to predict

        # Mask by calendar quarter, all tickers of the same quarter remain together
        train_mask = quarters_col.isin(train_quarters)
        test_mask  = quarters_col == test_quarter
        
        X_train, y_train = X[train_mask], y[train_mask]
        X_test,  y_test  = X[test_mask],  y[test_mask]

        # Impute NaNs using only training data stats
        X_train_imp, X_test_imp = impute_nans(X_train, X_test)

        model.fit(X_train_imp, y_train)
        y_pred = model.predict(X_test_imp)

        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        errors.append(rmse)

        fold_predictions.append(pd.DataFrame({
                "ticker":           tickers_col[test_mask].values,
                "quarter":          test_quarter,
                "predicted_return": y_pred,
                "actual_return":    y_test.values,
            })
        )

    avg_rmse = float(np.mean(errors))
    print(f"  {model_name:20} - avg RMSE: {avg_rmse:.4f}% over {len(errors)} test quarters")
    predictions_df = pd.concat(fold_predictions, ignore_index=True) if fold_predictions else pd.DataFrame()
    return avg_rmse, predictions_df


def train_final_model(X: pd.DataFrame, y: pd.Series, model) -> object:
    """
    Trains the chosen model on the full dataset.
    This is the model that gets saved to .pkl and used for predictions.
    """
    X_imp, _ = impute_nans(X, X)  # impute with full dataset median
    model.fit(X_imp, y)
    return model


def print_feature_importance(model, X: pd.DataFrame, model_name: str) -> dict:
    """
    Prints the top 15 most important features.
    This is the quant-readable part, shows which signals actually matter.
    """
    print(f"\nTop 15 features ({model_name}):")

    if hasattr(model, "feature_importances_"):
        # Random Forest and XGBoost
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        # OLS, coefficients instead of importances
        importances = np.abs(model.coef_)
    else:
        print("  Model does not expose feature importances.")
        return

    feature_names = X.columns.tolist()
    ranked = sorted(
        zip(feature_names, importances),
        key=lambda x: x[1], #X is the tuple: ex ("iowa_rainfall_mm", 0.12) so we take the importance
        reverse=True,   #and then we go from the largest to the smallest
    )

    for name, score in ranked[:15]:
        print(f"  {name:50} {score:.4f}")
    # Return full dict sorted by importance — used by save_training_run in __main__
    return {col: round(float(score), 6) for col, score in ranked}


def run_training() -> None: # this is basically __main__ fro external use
    from db.queries import read_ml_features, save_training_run
    print("Loading data from Supabase...")
    df = read_ml_features()

    print(f"Dataset shape: {df.shape}")
    print(f"Tickers: {df['ticker'].unique().tolist()}")

    X, y = prepare_data(df)
    quarters_col = df.loc[y.index, "quarter"]
    tickers_col  = df.loc[y.index, "ticker"]

    print(f"After prep: {X.shape[0]} rows, {X.shape[1]} features\n")

    # Define the 3 candidates
    models = {
        "OLS":           LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42), # 100 trees more = stability but slower, random state is just a random seed with 42 being convention
        "XGBoost":       XGBRegressor(n_estimators=100, random_state=42, verbosity=0), # 100 boosted trees etc, no terminal logs
        "LightGBM":      LGBMRegressor(n_estimators=100, random_state=42, verbose=-1), #saw it from linkedin post looked sick
    }

    # Walk-forward validation for each model
    print("Walk-forward validation:")
    print("-" * 50)
    results = {}
    fold_preds = {}
    for name, model in models.items():
        rmse, preds = walk_forward_cv(X, y, quarters_col, tickers_col, model, name)
        results[name] = (rmse, model)
        fold_preds[name] = preds

    # Pick the best model (lowest RMSE)
    best_name = min(results, key=lambda k: results[k][0])
    best_rmse, best_model = results[best_name]
    print(f"\nBest model: {best_name} (RMSE: {best_rmse:.4f}%)")

    # Train final model on full dataset and save
    print(f"\nTraining final {best_name} on full dataset...")
    final_model = train_final_model(X, y, best_model)

    joblib.dump({
        "model":        final_model,
        "model_name":   best_name,
        "feature_cols": X.columns.tolist(),  # saved so predict.py uses exact same columns
    }, MODEL_PATH)
    print(f"Saved to {MODEL_PATH}")

    baseline_rmse = float(y.std())
    print(f"  Baseline (predict 0%)  -> RMSE: {baseline_rmse:.4f}%")  # ASCII: Windows consoles choke on unicode arrows

    # Feature importance — the quant-readable part
    feature_importance_dict = print_feature_importance(final_model, X, best_name)
    save_training_run(
        best_model          = best_name,
        rmse_ols            = results["OLS"][0],
        rmse_rf             = results["Random Forest"][0],
        rmse_xgb            = results["XGBoost"][0],
        rmse_lgbm           = results["LightGBM"][0],
        best_rmse           = best_rmse,
        n_features          = X.shape[1],
        n_rows              = X.shape[0],
        start_year          = START_YEAR,
        train_quarters      = MIN_TRAIN_QUARTERS,
        feature_importance  = feature_importance_dict,
        baseline_rmse       = baseline_rmse,
    )

    from db.queries import upload_model
    upload_model()

    from db.queries import backfill_predictions
    backfill_predictions(fold_preds[best_name], model_version=best_name, min_quarter="2022Q1")


#TODO add directionnal accuracy logging and more complexe baselines to compare to (momentum, sector average)

if __name__ == "__main__":
    print("Loading data from Supabase...")
    df = read_ml_features()

    print(f"Dataset shape: {df.shape}")
    print(f"Tickers: {df['ticker'].unique().tolist()}")

    X, y = prepare_data(df)
    quarters_col = df.loc[y.index, "quarter"]

    print(f"After prep: {X.shape[0]} rows, {X.shape[1]} features\n")

    # Define the 3 candidates
    models = {
        "OLS":           LinearRegression(),
        "Random Forest": RandomForestRegressor(n_estimators=100, random_state=42), # 100 trees more = stability but slower, random state is just a random seed with 42 being convention
        "XGBoost":       XGBRegressor(n_estimators=100, random_state=42, verbosity=0), # 100 boosted trees etc, no terminal logs
        "LightGBM":      LGBMRegressor(n_estimators=100, random_state=42, verbose=-1), #saw it from linkedin post looked sick
    }

    # Walk-forward validation for each model
    print("Walk-forward validation:")
    print("-" * 50)
    results = {}
    for name, model in models.items():
        rmse = walk_forward_cv(X, y, quarters_col, model, name)
        results[name] = (rmse, model)

    # Pick the best model (lowest RMSE)
    best_name = min(results, key=lambda k: results[k][0])
    best_rmse, best_model = results[best_name]
    print(f"\nBest model: {best_name} (RMSE: {best_rmse:.4f}%)")

    # Train final model on full dataset and save
    print(f"\nTraining final {best_name} on full dataset...")
    final_model = train_final_model(X, y, best_model)

    joblib.dump({
        "model":        final_model,
        "model_name":   best_name,
        "feature_cols": X.columns.tolist(),  # saved so predict.py uses exact same columns
    }, MODEL_PATH)
    print(f"Saved to {MODEL_PATH}")

    baseline_rmse = float(y.std())
    print(f"  Baseline (predict 0%)  -> RMSE: {baseline_rmse:.4f}%")  # ASCII: Windows consoles choke on unicode arrows

    # Feature importance — the quant-readable part
    feature_importance_dict = print_feature_importance(final_model, X, best_name)
    save_training_run(
        best_model          = best_name,
        rmse_ols            = results["OLS"][0],
        rmse_rf             = results["Random Forest"][0],
        rmse_xgb            = results["XGBoost"][0],
        rmse_lgbm           = results["LightGBM"][0],
        best_rmse           = best_rmse,
        n_features          = X.shape[1],
        n_rows              = X.shape[0],
        start_year          = START_YEAR,
        train_quarters      = MIN_TRAIN_QUARTERS,
        feature_importance  = feature_importance_dict,
        baseline_rmse       = baseline_rmse,
    )