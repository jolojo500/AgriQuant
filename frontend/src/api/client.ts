import type {
  TickersResponse,
  PricesResponse,
  WeatherResponse,
  RankingsResponse,
  ReliabilityResponse,
  PredictionHistoryResponse,
} from '../types'

// VITE_API_URL should be in .env.local    
// Vite prefix is needed for vite to load it
const BASE_URL = import.meta.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

export const api = {
  getTickers:     ()               => get<TickersResponse>('/tickers'),
  getPrices:      (ticker: string) => get<PricesResponse>(`/prices/${ticker}`),
  getWeather:     ()               => get<WeatherResponse>('/weather/regions'),
  getRankings:    ()               => get<RankingsResponse>('/rankings'),
  getReliability: ()               => get<ReliabilityResponse>('/reliability'),
  getPredictions: (ticker: string) => get<PredictionHistoryResponse>(`/predictions/${ticker}`),
}