"""Dependency-free load test (Phase 12).

Hammers a running Beru backend with concurrent httpx workers and reports
throughput + latency percentiles per endpoint group.

Usage:
    # terminal A: start the server
    .\\.venv\\Scripts\\python -m uvicorn app.main:app --port 8000

    # terminal B: run the load test
    .\\.venv\\Scripts\\python -m scripts.load_test --base-url http://localhost:8000 --users 12 --duration 20

Exit code 1 if error rate > --max-error-rate or p95 exceeds --max-p95-ms.
"""

import argparse
import statistics
import threading
import time

import httpx

ENDPOINTS = ["health", "chat", "predictions", "audit"]


def _format_ms(value: float) -> str:
    return f"{value * 1000:.1f} ms"


class Worker:
    """One virtual user: logs in once, then issues requests in a loop."""

    def __init__(self, base_url: str, endpoint: str, results: dict, stop: threading.Event) -> None:
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
        self.endpoint = endpoint
        self.results = results
        self.stop = stop
        self.token: str | None = None

    def _login(self) -> bool:
        try:
            response = self.client.post(
                "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
            )
            if response.status_code == 200:
                self.token = response.json()["access_token"]
                return True
        except httpx.HTTPError:
            pass
        return False

    def _hit(self) -> tuple[str, float, int]:
        started = time.perf_counter()
        try:
            if self.endpoint == "health":
                response = self.client.get("/api/v1/health")
            elif self.endpoint == "chat":
                response = self.client.post(
                    "/api/v1/agents/chat",
                    json={"message": "which students are at risk of dropping out"},
                    headers={"Authorization": f"Bearer {self.token}"},
                )
            elif self.endpoint == "predictions":
                response = self.client.get(
                    "/api/v1/predictions/all?limit=25",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
            else:  # audit
                response = self.client.get(
                    "/api/v1/audit?limit=50",
                    headers={"Authorization": f"Bearer {self.token}"},
                )
        except httpx.HTTPError as exc:
            elapsed = time.perf_counter() - started
            return self.endpoint, elapsed, 0  # 0 = transport error
        elapsed = time.perf_counter() - started
        return self.endpoint, elapsed, response.status_code

    def run(self, duration: float) -> None:
        if not self._login():
            self.results["errors"].append(("login", 0.0, 0))
            return
        deadline = time.perf_counter() + duration
        while not self.stop.is_set() and time.perf_counter() < deadline:
            name, elapsed, status = self._hit()
            self.results["latencies"].append((name, elapsed))
            if status == 0 or status >= 400:
                self.results["errors"].append((name, elapsed, status))
        self.client.close()


def run_load_test(base_url: str, users: int, duration: float, endpoints: list[str]) -> dict:
    results = {"latencies": [], "errors": []}
    stop = threading.Event()
    workers = [Worker(base_url, endpoints[i % len(endpoints)], results, stop) for i in range(users)]

    started = time.perf_counter()
    threads = [threading.Thread(target=w.run, args=(duration,), daemon=True) for w in workers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    wall = time.perf_counter() - started

    per_endpoint: dict[str, list[float]] = {}
    for name, elapsed in results["latencies"]:
        per_endpoint.setdefault(name, []).append(elapsed)

    report = {
        "base_url": base_url,
        "users": users,
        "wall_seconds": round(wall, 2),
        "requests": len(results["latencies"]),
        "errors": len(results["errors"]),
        "throughput_rps": round(len(results["latencies"]) / wall, 1),
        "per_endpoint": {},
    }
    for name, samples in sorted(per_endpoint.items()):
        report["per_endpoint"][name] = {
            "count": len(samples),
            "mean_ms": round(statistics.mean(samples) * 1000, 1),
            "p50_ms": round(statistics.median(samples) * 1000, 1),
            "p95_ms": round(sorted(samples)[int(len(samples) * 0.95) - 1] * 1000, 1),
            "p99_ms": round(sorted(samples)[int(len(samples) * 0.99) - 1] * 1000, 1),
            "max_ms": round(max(samples) * 1000, 1),
        }
    return report


def print_report(report: dict) -> None:
    print("=" * 64)
    print("LOAD TEST REPORT — Beru backend")
    print("=" * 64)
    print(f"target      : {report['base_url']}  users: {report['users']}")
    print(f"wall time   : {report['wall_seconds']} s")
    print(f"requests    : {report['requests']}  errors: {report['errors']}")
    print(f"throughput  : {report['throughput_rps']} req/s")
    print("-" * 64)
    print(f"{'endpoint':<14}{'count':>8}{'mean':>10}{'p50':>10}{'p95':>10}{'p99':>10}{'max':>10}")
    for name, stats in report["per_endpoint"].items():
        print(
            f"{name:<14}{stats['count']:>8}{_format_ms(stats['mean_ms'] / 1000):>10}"
            f"{_format_ms(stats['p50_ms'] / 1000):>10}{_format_ms(stats['p95_ms'] / 1000):>10}"
            f"{_format_ms(stats['p99_ms'] / 1000):>10}{_format_ms(stats['max_ms'] / 1000):>10}"
        )
    print("=" * 64)


def main() -> int:
    parser = argparse.ArgumentParser(description="Beru load test (Phase 12)")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--duration", type=float, default=15.0)
    parser.add_argument("--endpoints", nargs="+", default=ENDPOINTS, choices=ENDPOINTS)
    parser.add_argument("--max-error-rate", type=float, default=0.05)
    parser.add_argument("--max-p95-ms", type=float, default=2000.0)
    args = parser.parse_args()

    report = run_load_test(args.base_url, args.users, args.duration, args.endpoints)
    print_report(report)

    error_rate = report["errors"] / max(1, report["requests"])
    worst_p95 = max((s["p95_ms"] for s in report["per_endpoint"].values()), default=0.0)
    ok = error_rate <= args.max_error_rate and worst_p95 <= args.max_p95_ms
    print(
        f"SLO: error_rate={error_rate:.1%} (<= {args.max_error_rate:.0%})  "
        f"max p95={worst_p95:.0f} ms (<= {args.max_p95_ms:.0f} ms)  => {'PASS' if ok else 'FAIL'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
