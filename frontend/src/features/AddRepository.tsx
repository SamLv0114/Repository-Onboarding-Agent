import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Github, LoaderCircle, Sparkles, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { client, type Repository } from "@/lib/api";

const RUNNING = new Set(["queued", "cloning", "onboarding"]);
const POLL_MS = 1500;

function statusText(repo: Repository) {
  if (repo.status === "queued") return "Waiting for another repository to finish onboarding...";
  if (repo.status === "cloning") return "Cloning repository...";
  if (repo.status === "onboarding") {
    const p = repo.progress;
    return p && p.total ? `Reading code and writing claims · ${p.done}/${p.total} chunks` : "Exploring files, README and commit history...";
  }
  if (repo.status === "ready") return `${repo.name} is ready. Ask questions or browse its memory.`;
  return repo.error ?? "Onboarding failed.";
}

export function AddRepository({ onChange, onReady }: { onChange: () => void; onReady: (repo: Repository) => void }) {
  const [url, setUrl] = useState("");
  const [job, setJob] = useState<Repository | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!job || !RUNNING.has(job.status)) return;
    const timer = setTimeout(async () => {
      try {
        const next = await client.repository(job.repository_id);
        setJob(next);
        if (next.status !== job.status) onChange();
        if (next.status === "ready") onReady(next);
      } catch (err) { setError(err instanceof Error ? err.message : "Lost track of onboarding"); }
    }, POLL_MS);
    return () => clearTimeout(timer);
  }, [job, onChange, onReady]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!url.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const repo = await client.addRepository(url.trim());
      setJob(repo); onChange();
      if (repo.status === "ready") onReady(repo);
    } catch (err) { setError(err instanceof Error ? err.message : "Unknown error"); }
    finally { setBusy(false); }
  }

  const running = job !== null && RUNNING.has(job.status);
  const progress = job?.progress?.total ? job.progress.done / job.progress.total : 0;
  return <Card className="mb-6 p-5">
    <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="flex shrink-0 items-center gap-2 text-sm font-semibold text-slate-200"><Sparkles className="size-4 text-blue-400"/>Learn a repository</div>
      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3.5 py-2.5 focus-within:border-blue-700">
        <Github className="size-4 shrink-0 text-slate-500"/>
        <input aria-label="GitHub repository link" value={url} onChange={e=>setUrl(e.target.value)} placeholder="https://github.com/owner/repo"
          className="min-w-0 flex-1 bg-transparent text-sm text-slate-200 outline-none placeholder:text-slate-600" disabled={running}/>
      </div>
      <Button type="submit" disabled={busy || running || !url.trim()}>{busy || running ? <LoaderCircle className="size-4 animate-spin"/> : null}{running ? "Onboarding..." : "Learn"}</Button>
    </form>
    {error && <p role="alert" className="mt-3 flex gap-2 text-sm text-rose-300"><TriangleAlert className="mt-0.5 size-4 shrink-0"/>{error}</p>}
    {job && <div className="mt-4 space-y-2">
      <p className={`flex items-center gap-2 text-sm ${job.status === "failed" ? "text-rose-300" : job.status === "ready" ? "text-emerald-300" : "text-slate-300"}`}>
        {job.status === "failed" ? <TriangleAlert className="size-4 shrink-0"/> : job.status === "ready" ? <CheckCircle2 className="size-4 shrink-0"/> : <LoaderCircle className="size-4 shrink-0 animate-spin"/>}
        {statusText(job)}
      </p>
      {running && <div className="h-1.5 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-blue-500 transition-all" style={{ width: `${Math.max(progress * 100, job.status === "onboarding" ? 4 : 2)}%` }}/></div>}
    </div>}
  </Card>;
}
