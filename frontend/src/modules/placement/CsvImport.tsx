import { useState, useRef } from "react";
import { Upload, CheckCircle2, FileSpreadsheet, ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

import { Button } from "@/core/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/core/components/ui/card";
import { Badge } from "@/core/components/ui/badge";
import { toast } from "@/core/components/ui/toast";
import { placementApi, type CsvPreviewResult } from "@/modules/placement/api";
import { useAuthStore } from "@/core/stores/auth";
import { cn } from "@/core/lib/utils";

const IMPORT_TYPES = [
  { key: "companies", label: "Companies", desc: "Partner company records" },
  { key: "jds", label: "Job Descriptions", desc: "Job descriptions linked to companies" },
  { key: "drives", label: "Placement Drives", desc: "Scheduled placement drives" },
  { key: "selections", label: "Selections", desc: "Student placement offers" },
] as const;

const REQUIRED_COLS: Record<string, string[]> = {
  companies: ["name"],
  jds: ["company_name", "title"],
  drives: ["title", "company_name", "drive_date"],
  selections: ["student_id"],
};

export function CsvImport() {
  const token = useAuthStore((s) => s.token);
  const fileRef = useRef<HTMLInputElement>(null);
  const [selectedType, setSelectedType] = useState<string>("companies");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreviewResult | null>(null);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{ imported: number; skipped: number; message: string } | null>(null);

  const handlePreview = async () => {
    if (!selectedFile || !token) return;
    try {
      const res = await placementApi.importPreview(selectedType, selectedFile, token);
      setPreview(res);
    } catch (err) {
      toast.error("Preview failed", err instanceof Error ? err.message : "Could not preview CSV");
    }
  };

  const handleImport = async () => {
    if (!selectedFile || !token) return;
    setImporting(true);
    try {
      const res = await placementApi.importConfirm(selectedType, selectedFile, token);
      setResult(res);
      toast.success("Import complete", res.message);
    } catch (err) {
      toast.error("Import failed", err instanceof Error ? err.message : "Could not import CSV");
    } finally {
      setImporting(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Link to="/placement" className="rounded-lg border border-[var(--border)] p-2 hover:bg-[var(--muted)]">
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-indigo-100 text-indigo-600">
            <FileSpreadsheet className="h-5 w-5" />
          </span>
          <div>
            <h1 className="text-lg font-semibold">CSV Bulk Import</h1>
            <p className="text-sm text-[var(--muted-foreground)]">Import companies, JDs, drives, or selections from CSV files</p>
          </div>
        </div>
      </div>

      {/* Step 1: Select type */}
      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">1. Select Import Type</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {IMPORT_TYPES.map(({ key, label, desc }) => (
              <button
                key={key}
                onClick={() => { setSelectedType(key); setPreview(null); setResult(null); setSelectedFile(null); }}
                className={cn(
                  "rounded-lg border p-3 text-left transition-colors",
                  selectedType === key ? "border-[var(--primary)] bg-[var(--primary)]/5" : "border-[var(--border)] hover:bg-[var(--muted)]"
                )}
              >
                <p className="text-sm font-medium">{label}</p>
                <p className="text-xs text-[var(--muted-foreground)]">{desc}</p>
              </button>
            ))}
          </div>
          <div className="mt-3 rounded-md bg-[var(--muted)]/50 px-3 py-2 text-xs text-[var(--muted-foreground)]">
            Required columns: {REQUIRED_COLS[selectedType]?.join(", ")}
          </div>
        </CardContent>
      </Card>

      {/* Step 2: Upload */}
      <Card className="card-shell">
        <CardHeader>
          <CardTitle className="text-sm font-semibold">2. Upload CSV File</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-3 rounded-lg border-2 border-dashed border-[var(--border)] px-6 py-8">
            <Upload className="h-8 w-8 text-[var(--muted-foreground)]" />
            <p className="text-sm text-[var(--muted-foreground)]">Choose a .csv file to import</p>
            <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
              Browse files
            </Button>
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) { setSelectedFile(f); setPreview(null); setResult(null); }
            }} />
          </div>
          {selectedFile && (
            <div className="mt-3 flex items-center justify-between rounded-md border border-[var(--border)] px-3 py-2">
              <div className="flex items-center gap-2">
                <FileSpreadsheet className="h-4 w-4 text-[var(--primary)]" />
                <span className="text-sm font-medium">{selectedFile.name}</span>
                <span className="text-xs text-[var(--muted-foreground)]">({(selectedFile.size / 1024).toFixed(1)} KB)</span>
              </div>
              <Button variant="outline" size="sm" onClick={handlePreview}>Preview</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Step 3: Preview */}
      {preview && (
        <Card className="card-shell">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-semibold">
              3. Preview
              {preview.can_import ? (
                <Badge tone="success">Ready to import</Badge>
              ) : (
                <Badge tone="destructive">{preview.error_count} errors</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-xs text-[var(--muted-foreground)]">
              {preview.total_rows} rows total · {preview.filename}
            </p>
            {preview.preview.length > 0 && (
              <div className="overflow-x-auto rounded-md border border-[var(--border)]">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-[var(--border)] bg-[var(--muted)] text-[var(--muted-foreground)]">
                      {Object.keys(preview.preview[0]).map((col) => (
                        <th key={col} className="px-3 py-1.5 font-medium">{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.preview.map((row, i) => (
                      <tr key={i} className="border-b border-[var(--border)]">
                        {Object.values(row).map((val, j) => (
                          <td key={j} className="px-3 py-1.5">{val || "—"}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {preview.validation_errors.length > 0 && (
              <div className="mt-3 max-h-40 overflow-y-auto">
                <p className="text-xs font-semibold text-red-600 mb-1">Validation Errors:</p>
                {preview.validation_errors.map((e, i) => (
                  <div key={i} className="text-xs text-red-600">
                    Row {e.row}: {e.errors.join(", ")}
                  </div>
                ))}
              </div>
            )}
            {preview.can_import && (
              <div className="mt-4 flex justify-end">
                <Button onClick={handleImport} disabled={importing}>
                  {importing ? "Importing..." : "Confirm Import"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Result */}
      {result && (
        <Card className="card-shell border-l-4 border-l-green-500">
          <CardContent className="flex items-center gap-3 py-4">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <div>
              <p className="text-sm font-medium">{result.message}</p>
              <p className="text-xs text-[var(--muted-foreground)]">
                {result.imported} imported, {result.skipped} skipped
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
