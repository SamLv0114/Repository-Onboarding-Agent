import { BookOpen, Database, FileCode2, GitCommitHorizontal, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import type { ArchitectureMemory } from "@/lib/api";

export function MemoryExplorer({ memory, loading }: { memory: ArchitectureMemory | null; loading: boolean }) {
  if (loading) return <Card className="p-8 text-sm text-slate-400">Loading memory...</Card>;
  if (!memory) return <Card className="p-8 text-sm text-slate-400">No architecture memory loaded. Check the backend connection.</Card>;
  return <div className="space-y-5 animate-enter">
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
      <div className="flex items-center gap-3"><span className="rounded-xl bg-blue-500/10 p-2.5"><Database className="size-5 text-blue-400"/></span><div><p className="text-sm font-semibold">Architecture memory</p><p className="text-xs text-slate-400">Claim-based knowledge store · demo data</p></div></div>
      <Badge><GitCommitHorizontal className="mr-1 size-3"/>{memory.snapshot_id}</Badge>
    </div>
    <div className="grid gap-4 md:grid-cols-2">
      {memory.claims.map(claim=><Card key={claim.claim_id} className="p-5">
        <div className="mb-4 flex justify-between gap-3"><span className="rounded-lg bg-slate-800 p-2"><BookOpen className="size-4 text-slate-400"/></span><Badge className={claim.status === "valid" ? "border-emerald-900 bg-emerald-950/50 text-emerald-300" : "border-amber-900 bg-amber-950/50 text-amber-300"}>{claim.status === "stale" && <ShieldAlert className="mr-1 size-3"/>}{claim.status}</Badge></div>
        <p className="text-base font-semibold text-white">{claim.title}</p><p className="mt-2 text-sm leading-6 text-slate-400">{claim.text}</p>
        <div className="mt-4 border-t border-slate-800 pt-3 space-y-2"><p className="eyebrow">EVIDENCE</p>{claim.evidence.map((e,i)=><div key={i} className="flex items-center gap-2 text-xs text-slate-400"><FileCode2 className="size-3.5 shrink-0 text-blue-400"/><span className="truncate font-mono">{e.path}</span><span className="ml-auto shrink-0 font-mono">L{e.start_line}–{e.end_line}</span></div>)}</div>
        <p className="mt-4 font-mono text-[10px] text-slate-600">{claim.claim_id}</p>
      </Card>)}
    </div>
  </div>;
}
