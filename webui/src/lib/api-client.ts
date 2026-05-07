import type {
  Company,
  Alert,
  ScoreData,
  RankedCompany,
  OutreachData,
  MeetingPrep,
  PipelineOpportunity,
  DealHealth,
  WarmIntro,
  HealthStatus,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text().catch(() => "Unknown error");
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Health
export const getHealth = () => api<HealthStatus>("/health");

// Companies
export const getCompanies = () => api<Company[]>("/companies");
export const addCompany = (data: { name: string; domain: string; alert_email?: string; alert_channels?: string[] }) =>
  api<Company>("/companies", { method: "POST", body: JSON.stringify(data) });
export const deleteCompany = (id: string) => api<void>(`/companies/${id}`, { method: "DELETE" });
export const triggerResearch = (id: string) => api<void>(`/companies/${id}/research`, { method: "POST" });
export const getAlerts = (id: string) => api<Alert[]>(`/companies/${id}/alerts`);

// Score
export const getScore = (companyName: string) => api<ScoreData>(`/score/${encodeURIComponent(companyName)}`);

// Rank
export const getRank = () => api<RankedCompany[]>("/rank");

// Outreach
export const generateOutreach = (companyName: string) =>
  api<OutreachData>(`/outreach/${encodeURIComponent(companyName)}`, { method: "POST" });

// Meeting Prep
export const getMeetingPrep = (companyName: string) =>
  api<MeetingPrep>(`/prep/${encodeURIComponent(companyName)}`, { method: "POST" });

// Pipeline
export const getPipeline = () => api<PipelineOpportunity[]>("/pipeline");
export const trackOpportunity = (data: Omit<PipelineOpportunity, "health_score">) =>
  api<PipelineOpportunity>("/pipeline/track", { method: "POST", body: JSON.stringify(data) });
export const untrackOpportunity = (name: string) =>
  api<void>(`/pipeline/track/${encodeURIComponent(name)}`, { method: "DELETE" });
export const getDealHealth = (name: string) => api<DealHealth>(`/pipeline/${encodeURIComponent(name)}/assess`);

// Warm Intro
export const getWarmIntro = (companyName: string, data: { target_role: string; domain: string }) =>
  api<WarmIntro>(`/warm-intro/${encodeURIComponent(companyName)}`, { method: "POST", body: JSON.stringify(data) });
