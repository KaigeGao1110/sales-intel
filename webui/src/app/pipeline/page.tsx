"use client";
import { useState } from "react";
import { usePipeline, useTrackOpportunity, useUntrackOpportunity } from "@/lib/use-api";
import { Card, CardContent, StageBadge, Skeleton } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Plus, Trash2, Heart } from "lucide-react";

const STAGES = ["discovery", "qualification", "proposal", "negotiation", "closed"] as const;
type Stage = (typeof STAGES)[number];

const stageLabels: Record<Stage, string> = {
  discovery: "Discovery",
  qualification: "Qualification",
  proposal: "Proposal",
  negotiation: "Negotiation",
  closed: "Closed",
};

export default function PipelinePage() {
  const { data: opportunities, isLoading } = usePipeline();
  const trackOpportunity = useTrackOpportunity();
  const untrackOpportunity = useUntrackOpportunity();
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ company_name: "", stage: "discovery" as Stage, expected_close: "", champion_contact: "" });

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.company_name) return;
    await trackOpportunity.mutateAsync({ ...form });
    setForm({ company_name: "", stage: "discovery", expected_close: "", champion_contact: "" });
    setShowAdd(false);
  };

  const byStage = STAGES.reduce((acc, s) => {
    acc[s] = opportunities?.filter((o) => o.stage === s) ?? [];
    return acc;
  }, {} as Record<Stage, typeof opportunities>);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Pipeline</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Track Opportunity
        </button>
      </div>

      {/* Kanban Board */}
      {isLoading ? (
        <div className="grid grid-cols-5 gap-4">
          {STAGES.map((s) => (
            <div key={s} className="space-y-3">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {STAGES.map((stage) => (
            <div key={stage} className="space-y-3">
              <div className="flex items-center gap-2 px-1">
                <StageBadge stage={stage} />
                <span className="text-xs text-gray-400">({byStage[stage]?.length ?? 0})</span>
              </div>
              <div className="space-y-2">
                {byStage[stage]?.map((opp) => (
                  <Card key={opp.company_name} className="!rounded-lg">
                    <CardContent className="p-3 space-y-2">
                      <div className="font-medium text-sm text-gray-900">{opp.company_name}</div>
                      <div className="flex items-center justify-between">
                        {opp.health_score !== undefined && (
                          <span className="flex items-center gap-1 text-xs text-gray-500">
                            <Heart className={`w-3 h-3 ${opp.health_score >= 70 ? "text-green-500" : opp.health_score >= 40 ? "text-yellow-500" : "text-red-500"}`} />
                            {opp.health_score}
                          </span>
                        )}
                        <button
                          onClick={() => {
                            if (confirm(`Remove ${opp.company_name} from pipeline?`))
                              untrackOpportunity.mutate(opp.company_name);
                          }}
                          className="p-1 rounded hover:bg-red-50 text-red-400 hover:text-red-500 ml-auto"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {byStage[stage]?.length === 0 && (
                  <div className="border border-dashed border-gray-200 rounded-lg p-4 text-center">
                    <p className="text-xs text-gray-400">No opportunities</p>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Track Opportunity">
        <form onSubmit={handleAdd} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
            <input
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Acme Corp"
              value={form.company_name}
              onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Stage</label>
            <select
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.stage}
              onChange={(e) => setForm((f) => ({ ...f, stage: e.target.value as Stage }))}
            >
              {STAGES.map((s) => (
                <option key={s} value={s}>{stageLabels[s]}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Expected Close</label>
            <input
              type="date"
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              value={form.expected_close}
              onChange={(e) => setForm((f) => ({ ...f, expected_close: e.target.value }))}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Champion Contact</label>
            <input
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="john@acme.com"
              value={form.champion_contact}
              onChange={(e) => setForm((f) => ({ ...f, champion_contact: e.target.value }))}
            />
          </div>
          <button
            type="submit"
            disabled={trackOpportunity.isPending}
            className="w-full py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            {trackOpportunity.isPending ? "Tracking..." : "Track Opportunity"}
          </button>
        </form>
      </Modal>
    </div>
  );
}
