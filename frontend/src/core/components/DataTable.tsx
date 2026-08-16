import { useState, useMemo, useCallback, ReactNode } from "react";
import { cn } from "@/core/lib/utils";
import { Input } from "@/core/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/core/components/ui/select";
import { Button } from "@/core/components/ui/button";
import { X, Search } from "lucide-react";

export interface ColumnFilter {
  key: string;
  label: string;
  type: "text" | "select" | "date" | "number";
  options?: { value: string; label: string }[];
}

export interface TableFilters {
  search?: string;
  columnFilters?: Record<string, string>;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
}

interface DataTableProps<T> {
  data: T[];
  columns: { key: string; label: string; render?: (item: T) => ReactNode }[];
  filters?: ColumnFilter[];
  defaultFilters?: TableFilters;
  onFiltersChange?: (filters: TableFilters) => void;
  className?: string;
  emptyMessage?: string;
  keyExtractor: (item: T) => string;
}

export function DataTable<T>({
  data,
  columns,
  filters = [],
  defaultFilters = {},
  onFiltersChange,
  className,
  emptyMessage = "No data available",
  keyExtractor,
}: DataTableProps<T>) {
  const [search, setSearch] = useState(defaultFilters.search ?? "");
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>(defaultFilters.columnFilters ?? {});
  const [sortBy, setSortBy] = useState(defaultFilters.sortBy ?? "");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">(defaultFilters.sortOrder ?? "asc");

  const filteredData = useMemo(() => {
    let result = [...data];

    // Search filter
    if (search) {
      const searchLower = search.toLowerCase();
      result = result.filter((item) =>
        columns.some((col) => {
          const value = item[col.key as keyof T];
          return String(value).toLowerCase().includes(searchLower);
        })
      );
    }

    // Column filters
    Object.entries(columnFilters).forEach(([key, value]) => {
      if (value) {
        const filter = filters.find((f) => f.key === key);
        if (!filter) return;

        result = result.filter((item) => {
          const itemValue = item[key as keyof T];
          const strValue = String(itemValue);

          if (filter.type === "select") {
            return strValue === value;
          }
          if (filter.type === "number") {
            return Number(itemValue) >= Number(value);
          }
          return strValue.toLowerCase().includes(value.toLowerCase());
        });
      }
    });

    // Sorting
    if (sortBy) {
      result.sort((a, b) => {
        const aVal = a[sortBy as keyof T];
        const bVal = b[sortBy as keyof T];
        const comparison = String(aVal).localeCompare(String(bVal));
        return sortOrder === "asc" ? comparison : -comparison;
      });
    }

    return result;
  }, [data, search, columnFilters, sortBy, sortOrder, columns, filters]);

  const handleSort = useCallback((key: string) => {
    if (sortBy === key) {
      setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortBy(key);
      setSortOrder("asc");
    }
  }, [sortBy]);

  const handleColumnFilterChange = useCallback((key: string, value: string) => {
    setColumnFilters((prev) => ({ ...prev, [key]: value }));
  }, []);

  const clearFilters = useCallback(() => {
    setSearch("");
    setColumnFilters({});
    setSortBy("");
    setSortOrder("asc");
  }, []);

  const hasActiveFilters = search || Object.values(columnFilters).some(Boolean) || sortBy;

  const currentFilters: TableFilters = {
    search,
    columnFilters,
    sortBy,
    sortOrder,
  };

  // Notify parent of filter changes
  if (onFiltersChange) {
    onFiltersChange(currentFilters);
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 p-3 bg-[var(--muted)]/30 rounded-lg border border-[var(--border)]">
        {/* Global Search */}
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--muted-foreground)]" />
          <Input
            placeholder="Search all columns..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-3"
          />
        </div>

        {/* Column Filters */}
        {filters.map((filter) => (
          <div key={filter.key} className="min-w-[150px]">
            {filter.type === "select" && filter.options && (
              <Select value={columnFilters[filter.key] ?? ""} onValueChange={(v) => handleColumnFilterChange(filter.key, v)}>
                <SelectTrigger className="h-9 w-full">
                  <SelectValue placeholder={filter.label} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All {filter.label}</SelectItem>
                  {filter.options.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            {(filter.type === "text" || filter.type === "number") && (
              <Input
                placeholder={filter.label}
                value={columnFilters[filter.key] ?? ""}
                onChange={(e) => handleColumnFilterChange(filter.key, e.target.value)}
                type={filter.type}
                className="h-9"
              />
            )}
          </div>
        ))}

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button variant="outline" size="sm" onClick={clearFilters}>
            <X className="mr-1.5 h-4 w-4" /> Clear
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-[var(--border)]">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-[var(--border)] bg-[var(--muted)]/30 text-xs text-[var(--muted-foreground)]">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    "py-2 px-3 font-semibold cursor-pointer select-none transition-colors hover:bg-[var(--muted)]",
                    sortBy === col.key && "bg-[var(--muted)]"
                  )}
                  onClick={() => handleSort(col.key)}
                  style={{ userSelect: "none" }}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {sortBy === col.key && (
                      <span className="text-[var(--primary)]">
                        {sortOrder === "asc" ? "↑" : "↓"}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-3 py-8 text-center text-[var(--muted-foreground)]">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr key={keyExtractor(item)} className="border-b border-[var(--border)] hover:bg-[var(--muted)]/30">
                  {columns.map((col) => (
                    <td key={col.key} className="py-2 px-3">
                      {col.render ? col.render(item) : String(item[col.key as keyof T] ?? "")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Results Info */}
      <div className="flex items-center justify-between text-sm text-[var(--muted-foreground)]">
        <span>Showing {filteredData.length} of {data.length} results</span>
        {hasActiveFilters && (
          <span className="text-[var(--primary)]">Filtered</span>
        )}
      </div>
    </div>
  );
}