from pydantic import BaseModel

#We forget about etls schemas because those validated data from apis, our api needs to send valid objects so we def new models here and also auto makes docs
#TODO unpack the dicts I put and make them into these for example return PriceResponse(**result) should work
class TickerInfo(BaseModel):
    ticker: str
    name:   str

class TickersResponse(BaseModel):
    tickers: list[TickerInfo]

class PriceRecord(BaseModel):
    date:   str
    close:  float
    volume: float

class PricesResponse(BaseModel):
    ticker: str
    prices: list[PriceRecord]

class WeatherRegion(BaseModel):
    region:      str
    lat:         float
    lon:         float
    rainfall_mm: float
    temp_max:    float
    humidity:    float

class WeatherResponse(BaseModel):
    regions: list[WeatherRegion]

class PredictionResponse(BaseModel):
    ticker:             str
    input_quarter:      str
    predicted_quarter:  str
    predicted_return:   float
    model:              str

class PredictionRecord(BaseModel):
    quarter:          str
    predicted_return: float
    actual_return:    float | None  # None until the quarter closes
    model_version:    str
    created_at:       str

class PredictionHistoryResponse(BaseModel):
    ticker:      str
    predictions: list[PredictionRecord]

class RankingRecord(BaseModel):
    ticker:           str
    predicted_return: float
    quarter:          str
    model_version:    str

class RankingsResponse(BaseModel):
    rankings: list[RankingRecord]

class ReliabilityRecord(BaseModel):
    ticker:             str
    direction_accuracy: float   # ex: 0.67 = good for 67 (lol)% of quarters
    n_predictions:      int     # closed quarters available to see

class ReliabilityResponse(BaseModel):
    rankings: list[ReliabilityRecord]

class TrainingRun(BaseModel):
    id:                 int
    best_model:         str
    rmse_ols:           float
    rmse_rf:            float
    rmse_xgb:           float
    rmse_lgbm:      float | None = None
    best_rmse:          float
    baseline_rmse:      float | None = None
    n_features:         int
    n_rows:             int
    start_year:         int
    train_quarters:     int
    feature_importance: dict[str, float] | None
    created_at:         str

class TrainingRunSummary(BaseModel):
    id:             int
    best_model:     str
    rmse_ols:       float
    rmse_rf:        float
    rmse_xgb:       float
    rmse_lgbm:      float | None = None
    best_rmse:      float
    baseline_rmse:  float | None = None
    n_features:     int
    n_rows:         int
    start_year:     int
    train_quarters: int
    created_at:     str

class TrainingHistoryResponse(BaseModel):
    runs: list[TrainingRunSummary]