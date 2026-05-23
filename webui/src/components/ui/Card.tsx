export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse bg-gray-200 rounded ${className}`} />;
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`bg-white rounded-xl border border-gray-200 shadow-sm ${className}`}>{children}</div>;
}

export function CardHeader({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`px-5 py-4 border-b border-gray-100 ${className}`}>{children}</div>;
}

export function CardContent({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

const gradeColors: Record<string, string> = {
  A: "bg-green-100 text-green-700",
  B: "bg-blue-100 text-blue-700",
  C: "bg-yellow-100 text-yellow-700",
  D: "bg-red-100 text-red-700",
};

export function GradeBadge({ grade }: { grade: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${gradeColors[grade] ?? "bg-gray-100 text-gray-600"}`}>
      {grade}
    </span>
  );
}

const severityColors: Record<string, string> = {
  critical: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-blue-100 text-blue-700",
};

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${severityColors[severity] ?? "bg-gray-100 text-gray-600"}`}>
      {severity}
    </span>
  );
}

const stageColors: Record<string, string> = {
  discovery: "bg-gray-100 text-gray-700",
  qualification: "bg-blue-100 text-blue-700",
  proposal: "bg-yellow-100 text-yellow-700",
  negotiation: "bg-orange-100 text-orange-700",
  closed: "bg-green-100 text-green-700",
};

export function StageBadge({ stage }: { stage: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${stageColors[stage] ?? "bg-gray-100 text-gray-600"}`}>
      {stage}
    </span>
  );
}
