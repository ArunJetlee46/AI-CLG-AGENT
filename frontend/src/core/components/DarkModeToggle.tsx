import { useEffect } from "react";
import { Moon, Sun, Monitor } from "lucide-react";
import { useThemeStore } from "@/core/stores/theme";
import { Button } from "@/core/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/core/components/ui/dropdown-menu";

export function DarkModeToggle() {
  const { theme, setTheme, resolvedTheme } = useThemeStore();

  useEffect(() => {
    useThemeStore.getState().initialize();
  }, []);

  const options = [
    { value: "light" as const, label: "Light", icon: Sun },
    { value: "dark" as const, label: "Dark", icon: Moon },
    { value: "system" as const, label: "System", icon: Monitor },
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-9 w-9 rounded-lg"
          aria-label="Toggle theme"
        >
          {resolvedTheme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-40">
        {options.map((option) => (
          <DropdownMenuItem
            key={option.value}
            onClick={() => setTheme(option.value)}
            className="flex items-center gap-2"
          >
            <option.icon className="h-4 w-4" />
            {option.label}
            {theme === option.value && (
              <span className="ml-auto text-xs text-[var(--primary)]">✓</span>
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}