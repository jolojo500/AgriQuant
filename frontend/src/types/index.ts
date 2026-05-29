// Exact mirror of the backend Pydantic schemas
// if schemas.py changes, update here too

export interface TickerInfo {
  ticker: string
  name: string
}

export interface TickersResponse {
  tickers: TickerInfo[]
}

export interface PriceRecord {
  date: string
  close: number
  volume: number
}

export interface PricesResponse {
  ticker: string
  prices: PriceRecord[]
}

export interface WeatherRegion {
  region: string
  lat: number
  lon: number
  rainfall_mm: number
  temp_max: number
  humidity: number
}

export interface WeatherResponse {
  regions: WeatherRegion[]
}

export interface PredictionRecord {
  quarter: string
  predicted_return: number
  actual_return: number | null  //null untill quarter closes
  model_version: string
  created_at: string
}

export interface PredictionHistoryResponse {
  ticker: string
  predictions: PredictionRecord[]
}

export interface RankingRecord {
  ticker: string
  predicted_return: number
  quarter: string
  model_version: string
}

export interface RankingsResponse {
  rankings: RankingRecord[]
}

export interface ReliabilityRecord {
  ticker: string
  direction_accuracy: number  // 0.0 to 1.0
  n_predictions: number       // closed quarters available
}

export interface ReliabilityResponse {
  rankings: ReliabilityRecord[]
}

export interface TrainingRun {
  id:               number
  best_model:       string
  rmse_ols:         number
  rmse_rf:          number
  rmse_xgb:         number
  best_rmse:        number
  baseline_rmse:    number
  n_features:       number
  n_rows:           number
  start_year:       number
  train_quarters:   number
  feature_importance: Record<string, number> | null  // only in /model/latest as to not have crazy delay
  created_at:       string
}

export interface TrainingHistoryResponse {
  runs: Omit<TrainingRun, 'feature_importance'>[]
}