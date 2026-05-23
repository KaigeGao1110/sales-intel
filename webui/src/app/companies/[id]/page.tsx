"use client";
import { useState } from "react";
import { use } from "react";
import { useCompanies, useScore, useAlerts, useTriggerResearch, useGenerateOutreach, useGeneratePrep } from "@/lib/use-api";
import { Card, CardHeader, CardContent, GradeBadge, SeverityBadge, Skeleton } from "@/components/ui/Card";
import { Globe, Bell, Loader2, Copy, CheckCircle, AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} className="p-1.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600" title="Copy">
      {copied ? <CheckCircle className="w-4 h-4 text-green-500" /> : <Copy className="w-4 h-4" />}
    </button>
  );
}

export default function CompanyDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: companies } = useCompanies();
  const company = companies?.find((c) => c.id === id);
  const [companyName, setCompanyName] = useState(company?.name ?? "");

  const { data: scoreData, isLoading: scoreLoading } = useScore(companyName);
  const { data: alerts, isLoading: alertsLoading } = useAlerts(id);
  const triggerResearch = useTriggerResearch();
  const generateOutreach = useGenerateOutreach();
  const generatePrep = useGeneratePrep();

  // Outreach state
  const [outreachData, setOutreachData] = useState<{
    cold_emails?: string[];
    linkedin_messages?: string[];
    subject_lines?: string[];
    angle?: string;
  } | null>(null);
  const [prepData, setPrepData] = useState<{ attendees?: string[]; meeting_time?: string } | null>(null);
  const [outreachCompany, setOutreachCompany] = useState("");
  const [prepCompany, setPrepCompany] = useState("");

  // Keep companyName in sync when company loads
  if (company && !companyName) setCompanyName(company.name);

  const gradeColor: Record<string, string> = {
    A: "text-green-600",
    B: "text-blue-600",
    C: "text-yellow-600",
    D: "text-red-600",
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{company?.name ?? "Company"}</h1>
          <div className="flex items-center gap-4 mt-1">
            <span className="flex items-center gap-1 text-sm text-gray-500">
              <Globe className="w-3.5 h-3.5" />
              {company?.domain ?? "—"}
            </span>
            <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
              company?.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
            }`}>
              {company?.status ?? "unknown"}
            </span>
          </div>
        </div>
        <button
          onClick={() => triggerResearch.mutate(id)}
          disabled={triggerResearch.isPending}
          className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          <Loader2 className={`w-4 h-4 ${triggerResearch.isPending ? "animate-spin" : ""}`} />
          Research
        </button>
      </div>

      {/* Score Card */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">ICP Score</h2>
        </CardHeader>
        <CardContent>
          {scoreLoading ? (
            <div className="flex items-center gap-4">
              <Skeleton className="w-24 h-24 rounded-full" />
              <div className="space-y-2 flex-1"><Skeleton className="h-4 w-48" /><Skeleton className="h-4 w-32" /></div>
            </div>
          ) : scoreData ? (
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <div className={`text-5xl font-bold ${gradeColor[scoreData.grade]}`}>{scoreData.score}</div>
                <GradeBadge grade={scoreData.grade} />
              </div>
              <div className="space-y-2">
                {scoreData.reasons.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-400 shrink-0" />
                    {r}
                  </div>
                ))}
              </div>
              <div className="flex items-start gap-2 p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
                {scoreData.recommended_action}
              </div>
            </div>
          ) : (
            <div className="text-sm text-gray-400">
              {companyName ? "Run research to generate ICP score" : "Company name not available"}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Alerts Timeline */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">Alerts Timeline</h2>
        </CardHeader>
        <CardContent className="p-0">
          {alertsLoading ? (
            <div className="p-5 space-y-3">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : alerts && alerts.length > 0 ? (
            <div className="divide-y divide-gray-50">
              {alerts.map((a) => (
                <div key={a.id} className="px-5 py-3 flex items-start gap-3">
                  <SeverityBadge severity={a.severity} />
                  <p className="text-sm text-gray-700 flex-1">{a.message}</p>
                  <span className="text-xs text-gray-400 whitespace-nowrap">
                    {new Date(a.timestamp).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-gray-400">
              <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No alerts for this company</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Outreach Generator */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">Outreach Generator</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <input
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Company name"
              value={outreachCompany}
              onChange={(e) => setOutreachCompany(e.target.value)}
            />
            <button
              onClick={async () => {
                if (!outreachCompany) return;
                const data = await generateOutreach.mutateAsync(outreachCompany);
                setOutreachData(data);
              }}
              disabled={!outreachCompany || generateOutreach.isPending}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {generateOutreach.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate"}
            </button>
          </div>
          {generateOutreach.isError && (
            <p className="text-sm text-red-500">Failed to generate outreach. Is the API running?</p>
          )}
          {outreachData && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
              {outreachData.angle && (
                <div className="p-3 bg-blue-50 rounded-lg text-sm text-blue-800">
                  <span className="font-medium">Angle:</span> {outreachData.angle}
                </div>
              )}
              {outreachData.subject_lines && outreachData.subject_lines.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Subject Lines</h4>
                  <div className="space-y-1">
                    {outreachData.subject_lines.map((s, i) => (
                      <div key={i} className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 px-3 py-2 rounded">
                        <span className="flex-1">{s}</span>
                        <CopyButton text={s} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {outreachData.cold_emails && outreachData.cold_emails.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Cold Emails</h4>
                  <div className="space-y-2">
                    {outreachData.cold_emails.map((e, i) => (
                      <div key={i} className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">
                        <div className="flex justify-between items-start">
                          <span className="flex-1 pr-2">{e}</span>
                          <CopyButton text={e} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {outreachData.linkedin_messages && outreachData.linkedin_messages.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">LinkedIn Messages</h4>
                  <div className="space-y-2">
                    {outreachData.linkedin_messages.map((m, i) => (
                      <div key={i} className="p-3 bg-gray-50 rounded-lg text-sm text-gray-700">
                        <div className="flex justify-between items-start">
                          <span className="flex-1 pr-2">{m}</span>
                          <CopyButton text={m} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </CardContent>
      </Card>

      {/* Meeting Prep */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">Meeting Prep</h2>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <input
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Company name"
              value={prepCompany}
              onChange={(e) => setPrepCompany(e.target.value)}
            />
            <button
              onClick={async () => {
                if (!prepCompany) return;
                const data = await generatePrep.mutateAsync(prepCompany);
                setPrepData(data);
              }}
              disabled={!prepCompany || generatePrep.isPending}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {generatePrep.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate"}
            </button>
          </div>
          {generatePrep.isError && (
            <p className="text-sm text-red-500">Failed to generate meeting prep. Is the API running?</p>
          )}
          {prepData && (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-3">
              {prepData.attendees && prepData.attendees.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Attendees</h4>
                  <div className="flex flex-wrap gap-2">
                    {prepData.attendees.map((a, i) => (
                      <span key={i} className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">{a}</span>
                    ))}
                  </div>
                </div>
              )}
              {prepData.meeting_time && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-1">Recommended Time</h4>
                  <p className="text-sm text-gray-600">{prepData.meeting_time}</p>
                </div>
              )}
            </motion.div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
