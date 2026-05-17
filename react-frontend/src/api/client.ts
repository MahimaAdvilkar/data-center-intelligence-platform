import axios from "axios";

// In dev, Vite proxies /gravity, /optimization, /cluster, /ai, /health → localhost:8000
// In production, set VITE_API_URL to the deployed backend URL
const BASE = import.meta.env.VITE_API_URL ?? "";

export const api = axios.create({ baseURL: BASE, timeout: 60_000 });

// ── Types ────────────────────────────────────────────────────────────────────

export interface GravityScore {
  city: string;
  score: number;
  rank: number;
}

export interface CityDetail {
  city: string;
  parameters: Record<string, number>;
  score: number;
}

export interface ClusterSummary {
  cluster: number;
  label: string;
  count: number;
  avg_pue: number;
  avg_energy_mw: number;
  avg_area_sqft: number;
}

export interface OptimizationResult {
  pareto_front: Array<{ energy_mw: number; pue: number; area_sqft: number }>;
  best_solution: { energy_mw: number; pue: number; area_sqft: number };
  generations: number;
}

export interface ClusterPrediction {
  cluster: number;
  label: string;
  probabilities: Record<string, number>;
}

export interface ChatResponse {
  response: string;
  tools_used: string[];
}

// ── Endpoints ────────────────────────────────────────────────────────────────

export const getGravityScores = (top_n = 13) =>
  api.get<{ scores: GravityScore[] }>("/gravity/scores", { params: { top_n } });

export const getCityDetail = (city_name: string) =>
  api.get<CityDetail>("/gravity/city", { params: { city_name } });

export const getClusterSummary = () =>
  api.get<{ clusters: ClusterSummary[] }>("/cluster/summary");

export const runOptimization = (params: {
  capacity_mw: number;
  max_pue: number;
  min_area_sqft: number;
  generations?: number;
}) => api.post<OptimizationResult>("/optimization/run", params);

export const predictCluster = (features: Record<string, number>) =>
  api.post<ClusterPrediction>("/cluster/predict", { features });

export const sendChat = (message: string, history: object[], api_key: string) =>
  api.post<ChatResponse>("/ai/chat", { message, history, api_key });
