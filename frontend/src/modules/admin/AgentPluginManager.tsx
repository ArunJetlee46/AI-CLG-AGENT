import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  Plus,
  Edit2,
  Trash2,
  ToggleLeft,
  ToggleRight,
  Bot,
} from "lucide-react";

import { PageHeader } from "@/core/components/PageHeader";
import { Badge } from "@/core/components/ui/badge";
import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader } from "@/core/components/ui/card";
import { Input } from "@/core/components/ui/input";
import { Textarea } from "@/core/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/core/components/ui/dialog";
import { api } from "@/core/lib/api";
import { useAuthStore } from "@/core/stores/auth";
import { cn } from "@/core/lib/utils";

interface AgentPlugin {
  name: string;
  description: string;
  intent_keywords: string[];
  priority: number;
  enabled: boolean;
  metadata: Record<string, unknown>;
}

export function AgentPluginManager() {
  const token = useAuthStore((s) => s.token);
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [editingPlugin, setEditingPlugin] = useState<AgentPlugin | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    intent_keywords: "",
    priority: 0,
    enabled: true,
  });

  const { data: plugins, isLoading, error } = useQuery({
    queryKey: ["agent-plugins"],
    queryFn: () => api<AgentPlugin[]>("/agent-plugins", {}, token!),
    enabled: !!token,
  });

  interface CreatePluginData {
  name: string;
  description: string;
  intent_keywords: string[];
  priority: number;
  enabled: boolean;
}

interface UpdatePluginData {
  description?: string;
  intent_keywords?: string[];
  priority?: number;
  enabled?: boolean;
}

  const createMutation = useMutation({
    mutationFn: (data: CreatePluginData) =>
      api<AgentPlugin>("/agent-plugins", { method: "POST", body: JSON.stringify(data) }, token!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent-plugins"] });
      setShowCreate(false);
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ name, data }: { name: string; data: UpdatePluginData }) =>
      api<AgentPlugin>(`/agent-plugins/${name}`, { method: "PATCH", body: JSON.stringify(data) }, token!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["agent-plugins"] });
      setEditingPlugin(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (name: string) =>
      api(`/agent-plugins/${name}`, { method: "DELETE" }, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-plugins"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ name, enable }: { name: string; enable: boolean }) =>
      api(`/agent-plugins/${name}/${enable ? "enable" : "disable"}`, { method: "POST" }, token!),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["agent-plugins"] }),
  });

  function resetForm() {
    setFormData({ name: "", description: "", intent_keywords: "", priority: 0, enabled: true });
  }

  function handleEdit(plugin: AgentPlugin) {
    setEditingPlugin(plugin);
    setFormData({
      name: plugin.name,
      description: plugin.description,
      intent_keywords: plugin.intent_keywords.join(", "),
      priority: plugin.priority,
      enabled: plugin.enabled,
    });
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data: CreatePluginData = {
      ...formData,
      intent_keywords: formData.intent_keywords.split(",").map((k) => k.trim()).filter(Boolean),
    };

    if (editingPlugin) {
      const { name, ...updateData } = data;
      updateMutation.mutate({ name: editingPlugin.name, data: updateData });
    } else {
      createMutation.mutate(data);
    }
  }

  const filteredPlugins = plugins?.filter(
    (p) =>
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description.toLowerCase().includes(search.toLowerCase()) ||
      p.intent_keywords.some((k) => k.toLowerCase().includes(search.toLowerCase()))
  ) ?? [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Agent Plugin Manager"
        subtitle="Manage dynamic specialist agents for the multi-agent system"
        icon={Bot}
        accent="bg-purple-100 text-purple-600"
      />

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogTrigger asChild>
          <Button>
            <Plus className="mr-1.5 h-4 w-4" /> Add Plugin
          </Button>
        </DialogTrigger>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Create New Agent Plugin</DialogTitle>
            <DialogDescription>
              Register a new specialist agent. Note: Handler logic must be implemented in the backend plugin module.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="grid gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Name</label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., research, career, finance"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What does this agent do?"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Intent Keywords (comma-separated)</label>
                <Input
                  value={formData.intent_keywords}
                  onChange={(e) => setFormData({ ...formData, intent_keywords: e.target.value })}
                  placeholder="research, paper, publication, cite"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Priority</label>
                  <Input
                    type="number"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                      className="rounded border-[var(--border)]"
                    />
                    <span className="text-sm">Enabled</span>
                  </label>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => { setShowCreate(false); resetForm(); }}>
                Cancel
              </Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Creating..." : "Create Plugin"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <div className="flex gap-2 mb-4">
        <Input
          placeholder="Search plugins..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-64"
        />
      </div>

      {isLoading && <p className="text-center text-[var(--muted-foreground)] py-8">Loading plugins...</p>}
      {error && <p className="text-center text-red-600 py-8">Failed to load plugins</p>}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredPlugins.map((plugin) => (
          <Card key={plugin.name} className="card-shell">
            <CardHeader className="flex flex-row items-start justify-between gap-4 pb-2">
              <div className="flex items-center gap-3">
                <Bot className={cn("h-8 w-8 rounded-lg", plugin.enabled ? "bg-purple-100 text-purple-600" : "bg-[var(--muted)] text-[var(--muted-foreground)]")} />
                <div>
                  <p className="font-semibold">{plugin.name}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">{plugin.intent_keywords.join(", ")}</p>
                </div>
              </div>
              <Badge tone={plugin.enabled ? "success" : "neutral"}>
                {plugin.enabled ? "Active" : "Disabled"}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-[var(--muted-foreground)]">{plugin.description}</p>
              <div className="flex items-center justify-between text-xs text-[var(--muted-foreground)]">
                <span>Priority: {plugin.priority}</span>
                <span>Keywords: {plugin.intent_keywords.length}</span>
              </div>
              <div className="flex items-center gap-2 pt-2 border-t border-[var(--border)]">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleEdit(plugin)}
                  disabled={updateMutation.isPending}
                >
                  <Edit2 className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => toggleMutation.mutate({ name: plugin.name, enable: !plugin.enabled })}
                  disabled={toggleMutation.isPending}
                >
                  {plugin.enabled ? <ToggleLeft className="h-4 w-4" /> : <ToggleRight className="h-4 w-4" />}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => deleteMutation.mutate(plugin.name)}
                  disabled={deleteMutation.isPending}
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {filteredPlugins.length === 0 && !isLoading && (
          <Card className="card-shell md:col-span-2 lg:col-span-3">
            <CardContent className="flex flex-col items-center justify-center gap-4 p-8 text-center">
              <Bot className="h-16 w-16 text-[var(--muted-foreground)]" />
              <p className="text-lg font-semibold">No plugins found</p>
              <p className="text-[var(--muted-foreground)]">Create your first agent plugin to extend the system</p>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog open={!!editingPlugin} onOpenChange={(open) => !open && setEditingPlugin(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Edit Plugin: {editingPlugin?.name}</DialogTitle>
            <DialogDescription>Modify the plugin configuration</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <input type="hidden" name="name" value={editingPlugin?.name} />
            <div className="grid gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Description</label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Intent Keywords (comma-separated)</label>
                <Input
                  value={formData.intent_keywords}
                  onChange={(e) => setFormData({ ...formData, intent_keywords: e.target.value })}
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium mb-1">Priority</label>
                  <Input
                    type="number"
                    value={formData.priority}
                    onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 0 })}
                  />
                </div>
                <div className="flex items-end">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.enabled}
                      onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                      className="rounded border-[var(--border)]"
                    />
                    <span className="text-sm">Enabled</span>
                  </label>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setEditingPlugin(null)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}