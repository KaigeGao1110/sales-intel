"use client";
import { useState } from "react";
import { useGenerateOutreach } from "@/lib/use-api";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { Loader2, Copy, CheckCircle, Zap } from "lucide-react";
import { motion } from "framer-motion";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1 px-2 py-1 rounded border border-gray-200 text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors"
    >
      {copied ? <><CheckCircle className="w-3 h-3 text-green-500" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
    </button>
  );
}

export default function OutreachPage() {
  const [companyName, setCompanyName] = useState("");
  const generateOutreach = useGenerateOutreach();
  const [result, setResult] = useState<{
    angle?: string;
    subject_lines?: string[];
    cold_emails?: string[];
    linkedin_messages?: string[];
  } | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!companyName) return;
    const data = await generateOutreach.mutateAsync(companyName);
    setResult(data);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-2xl font-semibold text-gray-900">Outreach Generator</h1>

      {/* Input Form */}
      <Card>
        <CardHeader>
          <h2 className="font-semibold text-gray-900">Generate Outreach</h2>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleGenerate} className="flex gap-2">
            <input
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter company name..."
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
            <button
              type="submit"
              disabled={!companyName || generateOutreach.isPending}
              className="flex items-center gap-2 px-5 py-2 bg-blue-500 text-white rounded-lg text-sm font-medium hover:bg-blue-600 disabled:opacity-50 transition-colors"
            >
              {generateOutreach.isPending ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating...</> : <><Zap className="w-4 h-4" /> Generate</>}
            </button>
          </form>
          {generateOutreach.isError && (
            <p className="mt-2 text-sm text-red-500">Failed to generate outreach. Is the API running?</p>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
          {result.angle && (
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-gray-900">Strategy Angle</h3>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 leading-relaxed">{result.angle}</p>
              </CardContent>
            </Card>
          )}

          {result.subject_lines && result.subject_lines.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-gray-900">Subject Lines</h3>
              </CardHeader>
              <CardContent className="space-y-2">
                {result.subject_lines.map((s, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    <span className="w-6 h-6 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-medium shrink-0">{i + 1}</span>
                    <span className="flex-1 text-gray-700 bg-gray-50 px-3 py-2 rounded">{s}</span>
                    <CopyButton text={s} />
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {result.cold_emails && result.cold_emails.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-gray-900">Cold Emails</h3>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.cold_emails.map((e, i) => (
                  <div key={i} className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-start gap-2 mb-2">
                      <span className="text-xs font-medium text-gray-500">Email {i + 1}</span>
                      <CopyButton text={e} />
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{e}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {result.linkedin_messages && result.linkedin_messages.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="font-semibold text-gray-900">LinkedIn Messages</h3>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.linkedin_messages.map((m, i) => (
                  <div key={i} className="p-4 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-start gap-2 mb-2">
                      <span className="text-xs font-medium text-gray-500">Message {i + 1}</span>
                      <CopyButton text={m} />
                    </div>
                    <p className="text-sm text-gray-700 whitespace-pre-wrap">{m}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </motion.div>
      )}

      {!result && !generateOutreach.isPending && (
        <div className="text-center py-16 text-gray-400">
          <Zap className="w-12 h-12 mx-auto mb-3 opacity-30" />
          <p className="text-sm font-medium">Enter a company name to generate outreach</p>
          <p className="text-xs mt-1">Get personalized cold emails, LinkedIn messages, and subject lines</p>
        </div>
      )}
    </div>
  );
}
