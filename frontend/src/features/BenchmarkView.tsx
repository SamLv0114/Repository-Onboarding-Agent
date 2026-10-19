import { Activity, ArrowLeftRight, Clock3, Coins, Gauge, Info, ListChecks } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { BenchmarkSummary } from "@/lib/api";

const metrics = [
  { title: "Answer accuracy", icon: ListChecks, subtitle: "Grounded answer correctness" },
  { title: "Response latency", icon: Clock3, subtitle: "p50 / p95 wall-clock time" },
  { title: "Token usage & cost", icon: Coins, subtitle: "Input / output / indexing" },
];
export function BenchmarkView({ summary }: { summary: BenchmarkSummary | null }) {
  return <div className="space-y-5 animate-enter">
    <Card className="border-blue-900/30 bg-blue-950/10 p-5">
      <div className="flex gap-3"><Info className="mt-1 size-5 shrink-0 text-blue-300"/><div><h2 className="font-semibold">Evaluation coming in the research phase</h2><p className="mt-1 text-sm leading-6 text-slate-400">The proposal compares memory-reuse against cold search. This scaffold intentionally shows no benchmark numbers until the team implements a reproducible evaluation suite.</p></div></div>
    </Card>
    <div className="grid gap-4 sm:grid-cols-3">{metrics.map(m=><Card key={m.title} className="p-5"><m.icon className="size-5 text-slate-400"/><p className="mt-4 text-sm font-medium text-slate-300">{m.title}</p><p className="mt-2 text-3xl font-semibold text-slate-500">—</p><p className="mt-2 text-xs text-slate-500">{m.subtitle}</p></Card>)}</div>
    <Card className="overflow-hidden"><div className="flex items-center gap-2 border-b border-slate-800 px-5 py-4"><ArrowLeftRight className="size-4 text-blue-400"/><p className="text-sm font-semibold">Strategy comparison</p></div>
      <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-slate-800 text-xs text-slate-500"><th className="px-5 py-3 font-medium">Metric</th><th className="px-5 py-3 font-medium">Memory first</th><th className="px-5 py-3 font-medium">Cold search</th></tr></thead><tbody>{["Accuracy","Median latency","Tokens / question","Cost / question"].map(m=><tr key={m} className="border-b border-slate-800/60 last:border-0"><td className="px-5 py-4 text-slate-300">{m}</td><td className="px-5 py-4 text-slate-500">Pending</td><td className="px-5 py-4 text-slate-500">Pending</td></tr>)}</tbody></table></div>
    </Card>
    <div className="flex items-center gap-2 text-xs text-slate-500"><Gauge className="size-4"/><span>{summary?.message ?? "Connect to FastAPI to load benchmark availability."}</span><Activity className="ml-auto size-4"/></div>
  </div>;
}
