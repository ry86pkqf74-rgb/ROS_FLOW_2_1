/**
 * Workflow Page
 *
 * The main workflow interface for authenticated users in LIVE mode.
 * Shows the full 19-stage research workflow with sidebar navigation.
 * Includes agent status section with real-time monitor and optional debugger.
 */

import { Header } from "@/components/header";
import { WorkflowPipeline } from "@/components/sections/workflow-pipeline";
import { AgentMonitor, AgentDebugger } from "@/components/agents";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

export default function WorkflowPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="pt-4 space-y-4">
        <section className="px-4" aria-label="Agent status">
          <AgentMonitor workflowId={undefined} />
          <Collapsible className="mt-4">
            <CollapsibleTrigger className="text-sm font-medium text-muted-foreground hover:text-foreground">
              Debug (trace, timing, I/O)
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="mt-2">
                <AgentDebugger workflowId={undefined} />
              </div>
            </CollapsibleContent>
          </Collapsible>
        </section>
        <WorkflowPipeline />
      </main>
    </div>
  );
}
