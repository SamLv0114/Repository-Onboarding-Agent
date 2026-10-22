import { useCallback, useEffect, useState } from "react";
import { Activity, BookMarked, Braces, ChevronDown, CircleHelp, Code2, Database, Github, Layers3, LayoutDashboard, Menu, MessageSquareText, PanelLeftClose, ShieldCheck, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AddRepository } from "@/features/AddRepository";
import { AskAgent } from "@/features/AskAgent";
import { BenchmarkView } from "@/features/BenchmarkView";
import { MemoryExplorer } from "@/features/MemoryExplorer";
import { client, type ArchitectureMemory, type BenchmarkSummary, type Repository } from "@/lib/api";

type Tab = "ask" | "memory" | "benchmark";
const navigation = [
  { id: "ask" as const, title: "Ask Agent", icon: MessageSquareText, desc: "Evidence-grounded QA" },
  { id: "memory" as const, title: "Memory Explorer", icon: Database, desc: "Stored architecture claims" },
  { id: "benchmark" as const, title: "Benchmark", icon: Activity, desc: "Compare strategies" },
];

function App() {
  const [tab, setTab] = useState<Tab>("ask");
  const [mobileMenu, setMobileMenu] = useState(false);
  const [apiOnline, setApiOnline] = useState(false);
  const [repos, setRepos] = useState<Repository[]>([]);
  const [repositoryId, setRepositoryId] = useState("demo-repo");
  const [memory, setMemory] = useState<ArchitectureMemory | null>(null);
  const [memoryLoading, setMemoryLoading] = useState(true);
  const [benchmarks, setBenchmarks] = useState<BenchmarkSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [memoryVersion, setMemoryVersion] = useState(0);
  const refreshRepos = useCallback(() => { client.repositories().then(setRepos).catch(() => {}); }, []);
  const openRepository = useCallback((repo: Repository) => { setRepositoryId(repo.repository_id); setMemoryVersion(v => v + 1); }, []);
  useEffect(() => {
    let alive = true;
    Promise.allSettled([client.health(), client.repositories(), client.benchmarks()]).then(results => {
      if (!alive) return;
      if (results[0].status === "fulfilled") setApiOnline(results[0].value.status === "ok");
      if (results[1].status === "fulfilled") setRepos(results[1].value);
      if (results[2].status === "fulfilled") setBenchmarks(results[2].value);
    });
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    let alive = true;
    setMemoryLoading(true);
    client.memory(repositoryId).then(m => { if (alive) { setMemory(m); setLoadError(null); } })
      .catch(err => { if (alive) { setMemory(null); setLoadError(err instanceof Error ? err.message : "Cannot load memory"); } })
      .finally(()=> { if (alive) setMemoryLoading(false); });
    return () => { alive = false; };
  }, [repositoryId, memoryVersion]);
  const current = navigation.find(n=>n.id===tab)!;
  return <div className="min-h-screen bg-[#0a101c] text-slate-100 lg:flex">
    {mobileMenu && <button type="button" aria-label="Close navigation" className="fixed inset-0 z-30 bg-black/70 lg:hidden" onClick={()=>setMobileMenu(false)} />}
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-[268px] flex-col border-r border-slate-800/90 bg-[#0d1422] transition-transform lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 ${mobileMenu ? "translate-x-0" : "-translate-x-full"}`}>
      <div className="flex h-[86px] items-center justify-between gap-3 border-b border-slate-800/70 px-5">
        <div className="flex items-center gap-3"><span className="flex size-10 items-center justify-center rounded-xl border border-blue-500/30 bg-blue-500/10 text-blue-300"><Braces className="size-5"/></span><div><p className="font-semibold tracking-tight">RepoLens<span className="text-blue-400">.</span></p><p className="text-[10px] font-medium tracking-[0.16em] text-slate-500">AMS 691 / RESEARCH</p></div></div>
        <button aria-label="Close sidebar" className="text-slate-500 lg:hidden" onClick={()=>setMobileMenu(false)}><X className="size-5"/></button>
      </div>
      <div className="px-4 pt-7"><p className="eyebrow px-3">WORKSPACE</p><nav className="mt-3 space-y-1" aria-label="Main navigation">{navigation.map(item=>{
        const Icon=item.icon;return <button type="button" key={item.id} onClick={()=>{setTab(item.id);setMobileMenu(false)}} className={`group flex w-full items-start gap-3 rounded-xl px-3.5 py-3.5 text-left transition ${tab===item.id ? "bg-blue-600/12 text-white ring-1 ring-blue-500/20" : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-200"}`}><Icon className={`mt-0.5 size-4 shrink-0 ${tab===item.id ? "text-blue-400" : "text-slate-500"}`}/><span><span className="block text-sm font-medium">{item.title}</span><span className="mt-1 block text-[11px] text-slate-500">{item.desc}</span></span></button>})}</nav></div>
      <div className="mt-8 px-4"><p className="eyebrow px-3">PROJECT STATUS</p><div className="mt-3 rounded-xl border border-slate-800 bg-slate-900/50 p-4"><div className="flex items-center justify-between"><span className="text-xs text-slate-300">Phase 01 / Foundation</span><span className="text-[11px] text-blue-300">In progress</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full w-1/6 rounded-full bg-blue-500"/></div><p className="mt-3 text-[11px] leading-5 text-slate-500">Memory contract · QA routing · source citations</p></div></div>
      <div className="mt-auto px-4 pb-6 pt-5"><div className="flex items-center gap-2 rounded-xl bg-slate-900/70 px-4 py-3 text-xs text-slate-500"><ShieldCheck className="size-4 text-emerald-400"/><span>Local development mode</span></div><div className="mt-4 flex items-center justify-between px-2 text-[11px] text-slate-600"><span>v0.1.0</span><span>October 2026</span></div></div>
    </aside>
    <main className="min-w-0 flex-1">
      <header className="flex h-[86px] items-center justify-between border-b border-slate-800/80 px-5 sm:px-8 lg:px-10">
        <div className="flex items-center gap-3"><button type="button" onClick={()=>setMobileMenu(true)} className="rounded-lg border border-slate-700 p-2 text-slate-400 lg:hidden" aria-label="Open navigation"><Menu className="size-4"/></button><div><p className="text-xs text-slate-500">Workspace / {current.title}</p><h1 className="mt-1 text-lg font-semibold tracking-tight">Repository Onboarding Agent</h1></div></div>
        <div className="flex items-center gap-3"><Badge className={apiOnline ? "border-emerald-800/60 bg-emerald-950/20 text-emerald-300" : "border-amber-900/70 bg-amber-950/30 text-amber-300"}><span className={`mr-2 size-1.5 rounded-full ${apiOnline ? "bg-emerald-400" : "bg-amber-400"}`}/>{apiOnline ? "API connected" : "API offline"}</Badge><span className="hidden rounded-lg border border-slate-800 p-2 text-slate-500 sm:block"><CircleHelp className="size-4"/></span></div>
      </header>
      <div className="mx-auto max-w-[1260px] px-5 pb-16 pt-8 sm:px-8 lg:px-10 lg:pt-10">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-5"><div><p className="eyebrow mb-3 flex items-center gap-2"><LayoutDashboard className="size-3.5"/> REPOSITORY INTELLIGENCE PLATFORM</p><h2 className="text-3xl font-semibold tracking-tight text-white sm:text-[34px]">{tab === "ask" ? "Understand any codebase." : tab === "memory" ? "Architecture, remembered." : "Measure what matters."}</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">{tab === "ask" ? "Ask architecture questions and inspect the source evidence behind every answer." : tab === "memory" ? "Browse the evidence-linked facts preserved during repository onboarding." : "Compare memory-reuse against cold search on a controlled evaluation set."}</p></div>
          <div className="flex min-w-[222px] items-center gap-2 rounded-xl border border-slate-800 bg-slate-900/50 px-3.5 py-2.5"><Github className="size-4 shrink-0 text-slate-400"/><select aria-label="Selected repository" value={repositoryId} onChange={e=>setRepositoryId(e.target.value)} className="min-w-0 flex-1 appearance-none bg-transparent text-sm text-slate-200 outline-none">{repos.length ? repos.map(r=><option className="bg-slate-900" key={r.repository_id} value={r.repository_id}>{r.name}{r.status === "ready" ? "" : ` · ${r.status.replace("_", " ")}`}</option>) : <option className="bg-slate-900" value="demo-repo">Demo Repository</option>}</select><ChevronDown className="size-4 text-slate-500"/></div>
        </div>
        <AddRepository onChange={refreshRepos} onReady={openRepository}/>
        {loadError && <div role="alert" className="mb-5 rounded-xl border border-amber-900/70 bg-amber-950/20 p-4 text-sm text-amber-200">{loadError}</div>}
        <div className="mb-6 grid gap-3 sm:grid-cols-3"><div className="stat"><Layers3 className="size-4 text-blue-400"/><div><p className="text-xs text-slate-500">Repository</p><p className="text-sm font-semibold text-slate-200">{repositoryId}</p></div></div><div className="stat"><BookMarked className="size-4 text-emerald-400"/><div><p className="text-xs text-slate-500">Memory claims</p><p className="text-sm font-semibold text-slate-200">{memory?.claims.length ?? "—"} stored</p></div></div><div className="stat"><Code2 className="size-4 text-violet-400"/><div><p className="text-xs text-slate-500">Snapshot</p><p className="truncate font-mono text-sm font-semibold text-slate-200">{repos.find(r=>r.repository_id===repositoryId)?.snapshot_id.slice(0, 12) || "—"}</p></div></div></div>
        {tab === "ask" ? <AskAgent repositoryId={repositoryId} memoryAvailable={repos.find(r=>r.repository_id===repositoryId)?.memory_available ?? true}/> : tab === "memory" ? <MemoryExplorer memory={memory} loading={memoryLoading}/> : <BenchmarkView summary={benchmarks}/>} 
        <footer className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t border-slate-800 pt-5 text-xs text-slate-600"><p>AMS 691 · Repository Onboarding Agent · Development scaffold</p><p className="flex items-center gap-2"><PanelLeftClose className="size-3.5"/> Designed for explainable, evidence-linked QA</p></footer>
      </div>
    </main>
  </div>;
}

export default App;
