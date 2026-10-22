import { useState, type FormEvent } from "react";
import { ArrowRight, BookOpen, CheckCircle2, Clock3, Code2, Database, FileCode2, GitFork, LoaderCircle, Search, Send, Sparkles, Terminal, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { client, type QAResponse, type Strategy } from "@/lib/api";

const examples = [
  "Where is authentication implemented?",
  "Which lines raise PermissionError?",
  "Where is database configuration defined?",
];

export function AskAgent({ repositoryId, memoryAvailable }: { repositoryId: string; memoryAvailable: boolean }) {
  const [question, setQuestion] = useState(examples[0]);
  const [strategy, setStrategy] = useState<Strategy>("memory_first");
  const [response, setResponse] = useState<QAResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim() || busy) return;
    setBusy(true); setError(null); setResponse(null);
    try { setResponse(await client.ask(question.trim(), strategy, repositoryId)); }
    catch (err) { setError(err instanceof Error ? err.message : "Unknown error"); }
    finally { setBusy(false); }
  }

  return <div className="space-y-6 animate-enter">
    <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
      <Card className="overflow-hidden border-slate-700/60">
        <div className="border-b border-slate-800 px-6 py-5 flex items-center justify-between">
          <div><p className="eyebrow">AGENT WORKSPACE</p><h2 className="mt-1 text-xl font-semibold text-white">Ask the codebase</h2></div>
          <Badge className="border-blue-800/60 bg-blue-950/40 text-blue-300"><Sparkles className="mr-1.5 size-3" />QA demo</Badge>
        </div>
        <form onSubmit={submit} className="space-y-5 p-6">
          <div>
            <label htmlFor="question" className="mb-2 block text-xs font-semibold uppercase tracking-widest text-slate-400">Your question</label>
            <Textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} rows={4} maxLength={2000}
              placeholder="Ask about architecture, files, dependencies..." />
          </div>
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Retrieval strategy</p>
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-950/80 p-1.5 border border-slate-800">
              <button type="button" onClick={()=>setStrategy("memory_first")} className={`rounded-lg px-3 py-3 text-left transition-colors ${strategy === "memory_first" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"}`}>
                <span className="flex items-center gap-2 text-sm font-medium"><Database className="size-4"/>Memory first</span>
                <span className={`mt-1 block text-xs ${memoryAvailable ? "text-slate-500" : "text-amber-400/80"}`}>{memoryAvailable ? "Reuse stored claims" : "No memory yet · will search code"}</span>
              </button>
              <button type="button" onClick={()=>setStrategy("cold_search")} className={`rounded-lg px-3 py-3 text-left transition-colors ${strategy === "cold_search" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"}`}>
                <span className="flex items-center gap-2 text-sm font-medium"><Search className="size-4"/>Cold search</span>
                <span className="mt-1 block text-xs text-slate-500">Search source directly</span>
              </button>
            </div>
          </div>
          <Button disabled={busy || !question.trim()} size="lg" type="submit" className="w-full justify-between">
            <span className="flex items-center gap-2">{busy ? <LoaderCircle className="size-4 animate-spin" /> : <Send className="size-4" />}{busy ? "Searching repository..." : "Run query"}</span><ArrowRight className="size-4" />
          </Button>
          {error && <p role="alert" className="flex gap-2 rounded-lg bg-rose-950/30 p-3 text-sm text-rose-300"><TriangleAlert className="mt-0.5 size-4 shrink-0"/>{error}</p>}
        </form>
      </Card>
      <div className="space-y-4">
        <Card className="p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200"><BookOpen className="size-4 text-blue-400"/>Example questions</div>
          <div className="mt-4 space-y-2">{examples.map((item,i) => <button key={i} onClick={()=>setQuestion(item)} type="button" className="flex w-full items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950/50 px-3.5 py-3 text-left text-sm text-slate-300 transition-colors hover:border-blue-700 hover:text-white"><span>{item}</span><ArrowRight className="size-3.5 shrink-0 text-slate-500"/></button>)}</div>
        </Card>
        <Card className="p-5 border-dashed">
          <div className="flex items-center gap-2 text-sm font-semibold"><Terminal className="size-4 text-emerald-400"/>What you'll build next</div>
          <p className="mt-2 text-sm leading-6 text-slate-400">Swap deterministic retrieval for an LLM-powered LangGraph flow, then evaluate memory reuse against cold search.</p>
          <p className="mt-3 text-xs text-slate-500">Current responses are from the synthetic fixture — not a real repository analysis.</p>
        </Card>
      </div>
    </div>
    {response && <Card className="animate-enter overflow-hidden border-slate-700/70">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-2"><CheckCircle2 className="size-4 text-emerald-400"/><span className="text-sm font-semibold">Query result</span>{response.is_demo && <Badge className="border-amber-800/60 bg-amber-950/30 text-amber-300">DEMO</Badge>}</div>
        <div className="flex items-center gap-3 text-xs text-slate-400"><span className="flex items-center gap-1"><GitFork className="size-3.5"/>{response.strategy_used.replaceAll("_", " ")}</span><span className="flex items-center gap-1"><Clock3 className="size-3.5"/>{response.elapsed_ms.toFixed(1)} ms</span>{response.usage && <span>{response.usage.llm_calls} LLM calls · {(response.usage.input_tokens + response.usage.output_tokens).toLocaleString()} tokens · {response.usage.tool_calls} tool calls</span>}</div>
      </div>
      <div className="space-y-5 p-6">
        {response.note && <p className="flex gap-2 rounded-lg border border-amber-900/60 bg-amber-950/20 p-3 text-sm text-amber-200"><TriangleAlert className="mt-0.5 size-4 shrink-0"/>{response.note}</p>}
        <div><p className="eyebrow mb-2">ANSWER</p><p className="text-sm leading-7 text-slate-200">{response.answer}</p></div>
        <div className="space-y-3"><p className="eyebrow">SOURCE EVIDENCE · {response.citations.length} CITATION{response.citations.length === 1 ? "" : "S"}</p>
          {response.citations.length === 0 && <p className="text-sm text-slate-500">No evidence found.</p>}
          {response.citations.map((item,i)=><div className="overflow-hidden rounded-xl border border-slate-800" key={`${item.path}-${item.start_line}-${i}`}>
            <div className="flex items-center justify-between gap-2 bg-slate-800/50 px-4 py-2.5"><span className="flex items-center gap-2 truncate font-mono text-xs text-blue-300"><FileCode2 className="size-3.5 shrink-0"/>{item.path}</span><span className="shrink-0 font-mono text-xs text-slate-400">L{item.start_line}–{item.end_line}</span></div>
            <pre className="overflow-auto whitespace-pre-wrap break-words bg-[#0b1423] px-4 py-3 text-xs leading-6 text-slate-300"><code>{item.preview}</code></pre>
          </div>)}
        </div>
        {response.matched_claim_ids.length > 0 && <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500"><Code2 className="size-3.5"/>Memory claims: {response.matched_claim_ids.join(", ")}</div>}
      </div>
    </Card>}
  </div>;
}
