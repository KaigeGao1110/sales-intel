import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "./api-client";
import { supabase } from "./supabase";
import type { Company, Alert, ScoreData, RankedCompany, PipelineOpportunity } from "./types";



// Health (still via FastAPI)
export const useHealth = () => useQuery({ queryKey: ["health"], queryFn: api.getHealth, refetchInterval: 30000 });

// Companies
export const useCompanies = () => useQuery({
  queryKey: ["companies"],
  queryFn: async () => {
    const { data, error } = await supabase.from('companies').select('*').order('created_at', { ascending: false });
    if (error) throw error;
    return data as Company[];
  },
});
export const useCompany = (id: string) => useQuery({
  queryKey: ["company", id],
  queryFn: async () => {
    const { data, error } = await supabase.from('companies').select('*').eq('id', id).single();
    if (error) throw error;
    return data as Company;
  },
  enabled: !!id,
});
export const useAddCompany = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.addCompany, onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }) });
};
export const useDeleteCompany = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.deleteCompany, onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }) });
};
export const useTriggerResearch = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.triggerResearch, onSuccess: () => qc.invalidateQueries({ queryKey: ["companies"] }) });
};
export const useAlerts = (companyId: string) => useQuery({
  queryKey: ["alerts", companyId],
  queryFn: async () => {
    const { data, error } = await supabase.from('alerts').select('*').eq('company_id', companyId).order('alert_date', { ascending: false });
    if (error) throw error;
    return data as Alert[];
  },
  enabled: !!companyId,
});

// Score
export const useScore = (companyName: string) => useQuery({
  queryKey: ["score", companyName],
  queryFn: async () => {
    const { data, error } = await supabase.from('scores').select('*').eq('company_name', companyName).order('created_at', { ascending: false }).limit(1).single();
    if (error) throw error;
    return data as ScoreData;
  },
  enabled: !!companyName,
});

// Rank
export const useRank = () => useQuery({
  queryKey: ["rank"],
  queryFn: async () => {
    const { data, error } = await supabase.from('scores').select('*').order('score', { ascending: false });
    if (error) throw error;
    return data as RankedCompany[];
  },
});

// Outreach
export const useOutreach = (companyName: string) =>
  useQuery({ queryKey: ["outreach", companyName], queryFn: () => api.generateOutreach(companyName), enabled: false });
export const useGenerateOutreach = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.generateOutreach, onSuccess: (_, name) => qc.invalidateQueries({ queryKey: ["outreach", name] }) });
};

// Meeting Prep
export const useMeetingPrep = (companyName: string) =>
  useQuery({ queryKey: ["prep", companyName], queryFn: () => api.getMeetingPrep(companyName), enabled: false });
export const useGeneratePrep = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.getMeetingPrep, onSuccess: (_, name) => qc.invalidateQueries({ queryKey: ["prep", name] }) });
};

// Pipeline
export const usePipeline = () => useQuery({
  queryKey: ["pipeline"],
  queryFn: async () => {
    const { data, error } = await supabase.from('pipeline').select('*').order('created_at', { ascending: false });
    if (error) throw error;
    return data as PipelineOpportunity[];
  },
});
export const usePipelineAssess = (companyName: string) => useQuery({
  queryKey: ["pipelineAssess", companyName],
  queryFn: async () => {
    const { data, error } = await supabase.from('pipeline').select('*').eq('company_name', companyName).single();
    if (error) throw error;
    return data as PipelineOpportunity;
  },
  enabled: !!companyName,
});
export const useTrackOpportunity = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.trackOpportunity, onSuccess: () => qc.invalidateQueries({ queryKey: ["pipeline"] }) });
};
export const useUntrackOpportunity = () => {
  const qc = useQueryClient();
  return useMutation({ mutationFn: api.untrackOpportunity, onSuccess: () => qc.invalidateQueries({ queryKey: ["pipeline"] }) });
};
export const useDealHealth = (name: string) =>
  useQuery({ queryKey: ["dealHealth", name], queryFn: () => api.getDealHealth(name), enabled: !!name });

// Warm Intro
export const useWarmIntro = () => useMutation({ mutationFn: ({ companyName, data }: { companyName: string; data: { target_role: string; domain: string } }) => api.getWarmIntro(companyName, data) });
