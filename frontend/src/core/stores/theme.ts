import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  resolvedTheme: "light" | "dark";
  setTheme: (theme: Theme) => void;
  initialize: () => void;
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function applyTheme(theme: "light" | "dark") {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: "system",
      resolvedTheme: "light",

      setTheme: (theme: Theme) => {
        const resolved = theme === "system" ? getSystemTheme() : theme;
        applyTheme(resolved);
        set({ theme, resolvedTheme: resolved });
      },

      initialize: () => {
        const { theme } = get();
        const resolved = theme === "system" ? getSystemTheme() : theme;
        applyTheme(resolved);
        set({ resolvedTheme: resolved });

        // Listen for system theme changes
        if (typeof window !== "undefined") {
          const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");
          const handleChange = () => {
            const { theme } = get();
            if (theme === "system") {
              const resolved = getSystemTheme();
              applyTheme(resolved);
              set({ resolvedTheme: resolved });
            }
          };
          mediaQuery.addEventListener("change", handleChange);
          // Store cleanup function
          (window as unknown as { __themeCleanup?: () => void }).__themeCleanup = () => {
            mediaQuery.removeEventListener("change", handleChange);
          };
        }
      },
    }),
    { name: "beru-theme" }
  )
);

// Initialize on load
if (typeof window !== "undefined") {
  useThemeStore.getState().initialize();
}