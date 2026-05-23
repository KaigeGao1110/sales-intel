export interface Company {
  id: string;
  name: string;
  domain: string;
  alert_email?: string;
  alert_channels?: string[];
  status?: string;
  last_checked?: string;
}

export interface Alert {
  id: string;
  company_id: string;
  severity: "critical" | "high" | "medium" | "low";
  message: string;
  timestamp: string;
}

export interface ScoreData {
  score: number;
  grade: "A" | "B" | "C" | "D";
  reasons: string[];
  recommended_action: string;
}

export interface RankedCompany {
  name: string;
  score: number;
  grade: "A" | "B" | "C" | "D";
  recommended_action: string;
}

export interface OutreachData {
  cold_emails: string[];
  linkedin_messages: string[];
  subject_lines: string[];
  angle: string;
}

export interface MeetingPrep {
  attendees: string[];
  meeting_time: string;
}

export interface PipelineOpportunity {
  company_name: string;
  stage: "discovery" | "qualification" | "proposal" | "negotiation" | "closed";
  expected_close?: string;
  champion_contact?: string;
  health_score?: number;
}

export interface DealHealth {
  score: number;
  factors: string[];
  recommendation: string;
}

export interface WarmIntro {
  target_role: string;
  domain: string;
  paths: string[];
}

export interface HealthStatus {
  status: string;
}
