import * as React from "react";
import { cn } from "@/lib/utils";

function Badge({ className, ...props }: React.ComponentProps<"span">) {
  return <span data-slot="badge" className={cn("inline-flex items-center rounded-full border border-slate-700 bg-slate-800/70 px-2.5 py-1 text-[11px] font-medium text-slate-300", className)} {...props} />;
}
export { Badge };
