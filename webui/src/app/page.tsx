"use client";
import { useState } from "react";
import { useRank, useCompanies, usePipeline, useAlerts, useAddCompany } from "@/lib/use-api";
import { Card, CardHeader, CardContent, GradeBadge, SeverityBadge, Skeleton } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Plus, Building2, Star, Bell, GitBranch } from "lucide-react";


export default function DashboardPage() {
  const [showAdd, setShowAdd] = useState(false);
  const { data: rankData, isLoading: rankLoading } = useRank();
  const { data: companies, isLoading: companiesLoading } = useCompanies();
  const { data: pipeline, isLoading: pipelineLoading } = usePipeline();

  const addCompany = useAddCompany();
  const [form, setForm] = useState({ name: "", domain: "", alert_email: "" });

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.domain) return;
    await addCompany.mutateAsync({ name: form.name, domain: form.domain, alert_email: form.alert_email });
    setForm({ name: "", domain: "", alert_email: "" });
    setShowAdd(false);
  };

  const highPriority = rankData?.filter((r) => r.grade === "A" || r.grade === "B").length ?? 0;

  // Get recent alerts from first company (simplified)
  const { data: alerts } = useAlerts(companies?.[0]?.id ?? "");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Company
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "Total Companies", value: companiesLoading ? undefined : companies?.length ?? 0, icon: Building2, color: "text-blue-500" },
          { label: "High Priority (A/B)", value: rankLoading ? undefined : highPriority, icon: Star, color: "text-green-500" },
          { label: "Recent Alerts", value: alerts?.length ?? 0, icon: Bell, color: "text-yellow-500" },
          { label: "Active Pipeline", value: pipelineLoading ? undefined : pipeline?.length ?? 0, icon: GitBranch, color: "text-purple-500" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label}>
            <CardContent className="p-5">
              {value === undefined ? (
                <Skeleton className="h-8 w-16 mb-2" />
              ) : (
                <div className="text-3xl font-bold text-gray-900">{value}</div>
              )}
              <div className="flex items-center gap-2 mt-1">
                <Icon className={`w-4 h-4 ${color}`} />
                <span className="text-sm text-gray-500">{label}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Priority Ranking Table */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">Priority Ranking</h2>
        </CardHeader>
        <CardContent className="p-0">
          {rankLoading ? (
            <div className="p-5 space-y-3">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
            </div>
          ) : rankData && rankData.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-5 py-3 font-medium text-gray-500">Rank</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Company</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Score</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Grade</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Recommended Action</th>
                  </tr>
                </thead>
                <tbody>
                  {rankData.map((r, i) => (
                    <tr key={r.name} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-5 py-3 text-gray-500">#{i + 1}</td>
                      <td className="px-5 py-3 font-medium text-gray-900">{r.name}</td>
                      <td className="px-5 py-3 text-gray-700">{r.score}</td>
                      <td className="px-5 py-3"><GradeBadge grade={r.grade} /></td>
                      <td className="px-5 py-3 text-gray-500 text-xs max-w-xs truncate">{r.recommended_action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-10 text-center text-gray-400">
              <Building2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No ranked companies yet. Add a company to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Alerts */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">Recent Alerts</h2>
        </CardHeader>
        <CardContent className="p-0">
          {alerts && alerts.length > 0 ? (
            <div className="divide-y divide-gray-50">
              {alerts.slice(0, 10).map((a) => (
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
            <div className="p-10 text-center text-gray-400">
              <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No alerts yet.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Company Modal */}
      <Modal open={showAdd} onClose={() => setShowAdd(false)} title="Add Company">
        <form onSubmit={handleAdd} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Company Name</label>
            <input
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Acme Corp"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Domain</label>
            <input
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="acme.com"
              value={form.domain}
              onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Alert Email</label>
            <input
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="alerts@acme.com"
              value={form.alert_email}
              onChange={(e) => setForm((f) => ({ ...f, alert_email: e.target.value }))}
            />
          </div>
          <button
            type="submit"
            disabled={addCompany.isPending}
            className="w-full py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
          >
            {addCompany.isPending ? "Adding..." : "Add Company"}
          </button>
        </form>
      </Modal>
    </div>
  );
}
