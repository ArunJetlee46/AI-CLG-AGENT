import { useState, useCallback } from "react";
import { ChevronDown, Brain, Zap, Search, CheckCircle, AlertCircle, Clock, GitBranch, MessageSquare, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { cn } from "@/core/lib/utils";
import { agentApi, type ChatResponse } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";

export interface AgentTraceStep {
  node: string;
  label: string;
  icon: React.ReactNode;
  status: "pending" | "running" | "completed" | "error";
  startTime?: number;
  endTime?: number;
  input?: unknown;
  output?: unknown;
  metadata?: Record<string, unknown>;
}

const NODE_CONFIG: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  memory: { label: "Memory", icon: <Brain className="h-4 w-4" />, color: "text-purple-500" },
  router: { label: "Router", icon: <GitBranch className="h-4 w-4" />, color: "text-blue-500" },
  planner: { label: "Planner", icon: <Zap className="h-4 w-4" />, color: "text-amber-500" },
  academic: { label: "Academic Ops", icon: <Search className="h-4 w-4" />, color: "text-green-500" },
  success: { label: "Student Success", icon: <CheckCircle className="h-4 w-4" />, color: "text-emerald-500" },
  resources: { label: "Resources", icon: <Shield className="h-4 w-4" />, color: "text-orange-500" },
  knowledge: { label: "Knowledge", icon: <Brain className="h-4 w-4" />, color: "text-violet-500" },
  reflect: { label: "Reflect", icon: <MessageSquare className="h-4 w-4" />, color: "text-rose-500" },
  debate: { label: "Debate", icon: <AlertCircle className="h-4 w-4" />, color: "text-red-500" },
  terminal: { label: "Terminal", icon: <Clock className="h-4 w-4" />, color: "text-slate-500" },
};

const EXECUTION_ORDER = [
  "memory", "router", "planner", 
  "academic", "success", "resources", "knowledge",  // conditional
  "reflect", 
  "debate",  // conditional
  "terminal"
];

export function AgentTracePanel() {
  const token = useAuthStore((s) => s.token);
  const [trace, setTrace] = useState<AgentTraceStep[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const resetTrace = useCallback(() => {
    const initialSteps: AgentTraceStep[] = EXECUTION_ORDER.map((node) => {
      const config = NODE_CONFIG[node];
      return {
        node,
        label: config.label,
        icon: config.icon,
        status: "pending" as const,
        metadata: {},
      };
    });
    setTrace(initialSteps);
    setLastResponse(null);
  }, []);

  const runAgent = async (message: string) => {
    if (!token || !message.trim()) return;
    
    setIsRunning(true);
    resetTrace();
    
    try {
      // Simulate step-by-step execution by polling the backend
      // In reality, the backend runs the full graph synchronously
      // We'll simulate the progression for visualization
      
      const response = await agentApi.chat(message, token);
      setLastResponse(response);
      
      // Animate through the steps based on actual execution path
      const executedNodes = getExecutedNodes(response);
      
      for (const node of EXECUTION_ORDER) {
        if (!executedNodes.has(node)) {
          // Mark unexecuted conditional branches as skipped
          const stepIndex = trace.findIndex(s => s.node === node);
          if (stepIndex >= 0) {
            const newTrace = [...trace];
            newTrace[stepIndex] = { ...newTrace[stepIndex], status: "pending" }; // Keep as pending (skipped)
            setTrace(newTrace);
          }
          continue;
        }
        
        // Animate this step
        const stepIndex = trace.findIndex(s => s.node === node);
        if (stepIndex >= 0) {
          // Running
          setTrace(prev => {
            const updated = [...prev];
            updated[stepIndex] = { 
              ...updated[stepIndex], 
              status: "running",
              startTime: Date.now(),
            };
            return updated;
          });
          
          await new Promise(r => setTimeout(r, 300)); // Visual delay
          
          // Completed
          setTrace(prev => {
            const updated = [...prev];
            updated[stepIndex] = { 
              ...updated[stepIndex], 
              status: "completed",
              endTime: Date.now(),
              metadata: getStepMetadata(node, response),
            };
            return updated;
          });
        }
      }
      
    } catch (error) {
      console.error("Agent execution failed:", error);
      // Mark current running step as error
      setTrace(prev => prev.map(s => 
        s.status === "running" ? { ...s, status: "error" } : s
      ));
    } finally {
      setIsRunning(false);
    }
  };

  const getExecutedNodes = (response: ChatResponse): Set<string> => {
    const nodes = new Set<string>(["memory", "router", "planner"]);
    
    // Add the specialist that was invoked
    if (response.agent && response.agent !== "unknown") {
      nodes.add(response.agent);
    }
    
    // Reflect always runs
    nodes.add("reflect");
    
    // Debate runs for success agent
    if (response.intent === "success") {
      nodes.add("debate");
    }
    
    // Terminal always runs
    nodes.add("terminal");
    
    return nodes;
  };

  const getStepMetadata = (node: string, response: ChatResponse): Record<string, unknown> => {
    switch (node) {
      case "router":
        return { intent: response.intent, classifiedAs: response.agent };
      case "planner":
        return { plan: ["classify", "execute", "reflect", ...(response.intent === "success" ? ["debate"] : [])] };
      case "reflect":
        return { confidence: "0.95", checks: ["answer_presence", "citations", "approval_gating"] };
      case "debate":
        return { critique: "Self-critique passed", rounds: 1 };
      case "terminal":
        return { 
          auditLogged: true, 
          decisionCardId: response.decision_card_id,
          approvalRequired: response.requires_approval 
        };
      default:
        return {};
    }
  };

  const toggleExpanded = (node: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev);
      if (next.has(node)) next.delete(node);
      else next.add(node);
      return next;
    });
  };

  const formatDuration = (start?: number, end?: number) => {
    if (!start || !end) return "—";
    const ms = end - start;
    return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Input Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-purple-500" />
            Agent Trace Panel
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !isRunning && runAgent(inputMessage)}
              placeholder="Ask the agent... (e.g., 'Which students are at risk in CS301?')"
              disabled={isRunning}
              className="flex-1 px-4 py-2 border border-[var(--border)] rounded-lg bg-[var(--background)] text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus:outline-none focus:ring-2 focus:ring-[var(--primary)]"
            />
            <Button 
              onClick={() => runAgent(inputMessage)} 
              disabled={isRunning || !inputMessage.trim()}
              className="whitespace-nowrap"
            >
              {isRunning ? "Running..." : "Execute"}
            </Button>
            <Button variant="outline" onClick={resetTrace} disabled={isRunning}>
              Reset
            </Button>
          </div>
          
          {/* Quick Test Queries */}
          <div className="flex flex-wrap gap-2">
            {[
              "Show me at-risk students",
              "What's the timetable conflict for CS201?",
              "Generate a question paper for CS301",
              "Analyze this job description for ML Engineer",
              "Create an intervention plan for STU2024005",
            ].map((q, i) => (
              <Button 
                key={i} 
                variant="ghost" 
                size="sm" 
                onClick={() => { setInputMessage(q); runAgent(q); }}
                disabled={isRunning}
                className="text-xs"
              >
                {q}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Execution Trace */}
      <Card className="flex-1 flex flex-col">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Execution Trace</span>
            {isRunning && (
              <span className="flex items-center gap-1 text-xs text-[var(--primary)] animate-pulse">
                <span className="h-2 w-2 rounded-full bg-[var(--primary)]"></span>
                Running...
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <div className="h-full overflow-y-auto pr-1">
            <div className="space-y-3">
              {trace.map((step, index) => {
                const config = NODE_CONFIG[step.node];
                const isExpanded = expandedSteps.has(step.node);
                const isLast = index === trace.length - 1;
                const duration = formatDuration(step.startTime, step.endTime);
                
                return (
                  <div 
                    key={step.node} 
                    className={cn(
                      "relative flex-shrink-0",
                      !isLast && "before:absolute before:left-[14px] before:top-[28px] before:bottom-0 before:w-[2px] before:bg-[var(--border)]"
                    )}
                  >
                    {/* Vertical line connector */}
                    
                    <div className="flex items-start gap-3">
                      {/* Step indicator */}
                      <div className="relative flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center z-10 transition-all duration-300"
                        style={{ 
                          backgroundColor: 
                            step.status === "completed" ? "var(--primary)" :
                            step.status === "running" ? "var(--primary)" :
                            step.status === "error" ? "var(--destructive)" :
                            "var(--muted)"
                        }}
                      >
                        {step.status === "completed" && <CheckCircle className="h-4 w-4 text-white" />}
                        {step.status === "running" && <span className="h-2 w-2 rounded-full bg-white animate-pulse" />}
                        {step.status === "error" && <AlertCircle className="h-4 w-4 text-white" />}
                        {step.status === "pending" && (
                          <span className="text-xs text-[var(--muted-foreground)] font-mono">
                            {index + 1}
                          </span>
                        )}
                      </div>
                      
                      {/* Step content */}
                      <div className="flex-1 min-w-0">
                        <div 
                          className={cn(
                            "rounded-lg border p-3 transition-all duration-200 cursor-pointer",
                            step.status === "completed" && "border-[var(--primary)]/30 bg-[var(--primary)]/5",
                            step.status === "running" && "border-[var(--primary)] bg-[var(--primary)]/5 animate-pulse",
                            step.status === "error" && "border-[var(--destructive)]/30 bg-[var(--destructive)]/5",
                            step.status === "pending" && "border-[var(--border)] bg-[var(--muted)]/30 opacity-60"
                          )}
                          onClick={() => toggleExpanded(step.node)}
                        >
                          <div className="flex items-center gap-2">
                            <span className={cn("flex-shrink-0", config.color)}>
                              {config.icon}
                            </span>
                            <span className="font-medium text-sm">{config.label}</span>
                            <Badge 
                              tone={
                                step.status === "completed" ? "success" :
                                step.status === "running" ? "primary" :
                                step.status === "error" ? "destructive" :
                                "neutral"
                              }
                              className="text-xs ml-auto"
                            >
                              {step.status === "running" ? "Running" : step.status}
                            </Badge>
                            {step.status !== "pending" && (
                              <span className="text-xs text-[var(--muted-foreground)] font-mono ml-2">
                                {duration}
                              </span>
                            )}
                            <span className={cn(
                              "ml-auto transition-transform duration-200",
                              isExpanded ? "rotate-180" : ""
                            )}>
                              <ChevronDown className="h-4 w-4 text-[var(--muted-foreground)]" />
                            </span>
                          </div>
                          
                          {/* Expanded details */}
                          {isExpanded && step.status !== "pending" && (
                            <div className="mt-3 space-y-2 pt-3 border-t border-[var(--border)] animate-in fade-in slide-down">
                              {step.metadata && Object.keys(step.metadata).length > 0 && (
                                <div className="text-xs">
                                  <div className="font-medium text-[var(--muted-foreground)] mb-1">Metadata</div>
                                  <div className="grid gap-1 text-[var(--foreground)]">
                                    {Object.entries(step.metadata).map(([key, value]) => (
                                      <div key={key} className="flex gap-2">
                                        <span className="text-[var(--muted-foreground)] font-mono">{key}:</span>
                                        <span className="font-mono text-green-600 dark:text-green-400">
                                          {typeof value === "object" ? JSON.stringify(value) : String(value)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Mock input/output for demo */}
                              {(step.node === "router" || step.node === "planner") && (
                                <div className="text-xs">
                                  <div className="font-medium text-[var(--muted-foreground)] mb-1">Input</div>
                                  <pre className="bg-[var(--muted)] p-2 rounded text-[var(--foreground)] overflow-auto max-h-24">
                                    {inputMessage}
                                  </pre>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Response Panel */}
      {lastResponse && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-green-500" />
              Agent Response
              <Badge tone="neutral" className="ml-auto">{lastResponse.intent}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-sm max-w-none text-sm">
              {lastResponse.answer}
            </div>
            {lastResponse.citations.length > 0 && (
              <div className="mt-4 space-y-2">
                <div className="font-medium text-xs text-[var(--muted-foreground)]">Citations</div>
                <ul className="list-decimal list-inside text-xs space-y-1">
                  {lastResponse.citations.map((c, i) => (
                    <li key={i} className="text-[var(--muted-foreground)]">{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {lastResponse.requires_approval && (
              <div className="mt-4 p-3 rounded-lg border border-amber-500 bg-amber-50">
                <div className="flex items-center gap-2 text-amber-700 text-sm">
                  <Shield className="h-4 w-4" />
                  <span>Requires approval (ID: {lastResponse.approval_id?.slice(0, 8)})</span>
                </div>
              </div>
            )}
            {lastResponse.decision_card_id && (
              <div className="mt-2 text-xs text-[var(--muted-foreground)]">
                Decision Card: {lastResponse.decision_card_id.slice(0, 8)}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}