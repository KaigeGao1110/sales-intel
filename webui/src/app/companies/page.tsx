"use client";
import { useState } from "react";
import { useCompanies, useAddCompany, useDeleteCompany, useTriggerResearch } from "@/lib/use-api";
import { Card, CardContent, Skeleton } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { Plus, Trash2, Search, Loader2 } from "lucide-react";
import Link from "next/link";

export default function CompaniesPage() {
  const { data: companies, isLoading } = useCompanies();
  const addCompany = useAddCompany();
  const deleteCompany = useDeleteCompany();
  const triggerResearch = useTriggerResearch();
  const [showAdd, setShowAdd] = useState(false);
  const [search, setSearch] = useState("");
  const [form, setForm] = useState({ name: "", domain: "", alert_email: "" });

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name || !form.domain) return;
    await addCompany.mutateAsync({ name: form.name, domain: form.domain, alert_email: form.alert_email });
    setForm({ name: "", domain: "", alert_email: "" });
    setShowAdd(false);
  };

  const filtered = companies?.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.domain.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold text-gray-900">Companies</h1>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          Add Company
        </button>
      </div>

      {/* Search */}
      {companies && companies.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Search companies..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      )}

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-5 space-y-3">
              {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
            </div>
          ) : filtered && filtered.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 text-left">
                    <th className="px-5 py-3 font-medium text-gray-500">Name</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Domain</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Status</th>
                    <th className="px-5 py-3 font-medium text-gray-500">Last Checked</th>
                    <th className="px-5 py-3 font-medium text-gray-500 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => (
                    <tr key={c.id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="px-5 py-3">
                        <Link href={`/companies/${c.id}`} className="font-medium text-blue-600 hover:underline">
                          {c.name}
                        </Link>
                      </td>
                      <td className="px-5 py-3 text-gray-500">{c.domain}</td>
                      <td className="px-5 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${
                          c.status === "active" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"
                        }`}>
                          {c.status ?? "unknown"}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-gray-500 text-xs">
                        {c.last_checked ? new Date(c.last_checked).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-5 py-3">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => triggerResearch.mutate(c.id)}
                            disabled={triggerResearch.isPending}
                            className="p-1.5 rounded hover:bg-blue-50 text-blue-500 disabled:opacity-50"
                            title="Trigger Research"
                          >
                            <Loader2 className={`w-4 h-4 ${triggerResearch.isPending ? "animate-spin" : ""}`} />
                          </button>
                          <Link
                            href={`/companies/${c.id}`}
                            className="px-3 py-1.5 rounded border border-gray-200 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
                          >
                            View
                          </Link>
                          <button
                            onClick={() => {
                              if (confirm(`Remove ${c.name}?`)) deleteCompany.mutate(c.id);
                            }}
                            className="p-1.5 rounded hover:bg-red-50 text-red-500"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-16 text-center text-gray-400">
              <Search className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm font-medium">No companies found</p>
              <p className="text-xs mt-1">
                {search ? "Try a different search term" : "Add your first company to get started"}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

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
