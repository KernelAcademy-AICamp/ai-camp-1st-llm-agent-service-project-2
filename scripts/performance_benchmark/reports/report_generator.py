#!/usr/bin/env python3
"""
Report Generator for Performance Benchmark Comparison

Compares two benchmark results and generates a Markdown report.

Usage:
    python report_generator.py \
        --baseline results/phase3_baseline_v1.json \
        --current results/phase4_langgraph_v1.json \
        --output reports/phase4_comparison.md
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class ReportGenerator:
    """Generates comparison reports from benchmark results"""

    def __init__(self, baseline_path: str, current_path: str):
        self.baseline = self._load_results(baseline_path)
        self.current = self._load_results(current_path)
        self.baseline_name = baseline_path
        self.current_name = current_path

    def _load_results(self, path: str) -> Dict[str, Any]:
        """Load benchmark results from JSON file"""
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _calculate_change(
        self,
        baseline_val: float,
        current_val: float,
        lower_is_better: bool = True
    ) -> Dict[str, Any]:
        """Calculate percentage change between values"""
        if baseline_val == 0:
            return {"change_pct": 0, "direction": "unchanged", "improved": False}

        change = current_val - baseline_val
        change_pct = (change / baseline_val) * 100

        if lower_is_better:
            improved = change < 0
        else:
            improved = change > 0

        if abs(change_pct) < 1:
            direction = "unchanged"
        elif change > 0:
            direction = "increase"
        else:
            direction = "decrease"

        return {
            "baseline": baseline_val,
            "current": current_val,
            "change": change,
            "change_pct": round(change_pct, 2),
            "direction": direction,
            "improved": improved
        }

    def _format_change(self, change: Dict[str, Any], unit: str = "") -> str:
        """Format change for display"""
        pct = change["change_pct"]
        if change["direction"] == "unchanged":
            return "~ (no change)"

        symbol = "+" if pct > 0 else ""
        emoji = "" if change["improved"] else ""

        return f"{emoji} {symbol}{pct:.1f}%"

    def _format_value(self, value: float, unit: str) -> str:
        """Format value with unit"""
        if unit == "ms":
            return f"{value:.0f}ms"
        elif unit == "usd":
            return f"${value:.4f}"
        elif unit == "%":
            return f"{value:.1f}%"
        else:
            return f"{value:.2f}"

    def generate_executive_summary(self) -> str:
        """Generate executive summary section"""
        baseline_summary = self.baseline.get("summary", {}).get("overall", {})
        current_summary = self.current.get("summary", {}).get("overall", {})

        # Calculate key metrics
        duration_change = self._calculate_change(
            baseline_summary.get("avg_duration_ms", 0),
            current_summary.get("avg_duration_ms", 0),
            lower_is_better=True
        )

        cost_change = self._calculate_change(
            baseline_summary.get("total_cost_usd", 0),
            current_summary.get("total_cost_usd", 0),
            lower_is_better=True
        )

        success_change = self._calculate_change(
            baseline_summary.get("success_rate", 0),
            current_summary.get("success_rate", 0),
            lower_is_better=False
        )

        # Build summary
        lines = []
        lines.append("## Executive Summary\n")

        # Duration improvement
        if duration_change["improved"]:
            lines.append(f"- **Response Time**: {abs(duration_change['change_pct']):.1f}% faster "
                        f"({self._format_value(duration_change['baseline'], 'ms')} → "
                        f"{self._format_value(duration_change['current'], 'ms')})")
        else:
            lines.append(f"- **Response Time**: {abs(duration_change['change_pct']):.1f}% slower "
                        f"({self._format_value(duration_change['baseline'], 'ms')} → "
                        f"{self._format_value(duration_change['current'], 'ms')})")

        # Cost change
        if cost_change["improved"]:
            lines.append(f"- **Cost**: {abs(cost_change['change_pct']):.1f}% reduction "
                        f"({self._format_value(cost_change['baseline'], 'usd')} → "
                        f"{self._format_value(cost_change['current'], 'usd')})")
        else:
            lines.append(f"- **Cost**: {abs(cost_change['change_pct']):.1f}% increase "
                        f"({self._format_value(cost_change['baseline'], 'usd')} → "
                        f"{self._format_value(cost_change['current'], 'usd')})")

        # Success rate
        lines.append(f"- **Success Rate**: "
                    f"{self._format_value(current_summary.get('success_rate', 0), '%')} "
                    f"({self._format_change(success_change)})")

        lines.append("")
        return "\n".join(lines)

    def generate_detailed_comparison(self) -> str:
        """Generate detailed comparison tables"""
        lines = []
        lines.append("## Detailed Comparison\n")

        # Get summaries for each category
        baseline_summary = self.baseline.get("summary", {})
        current_summary = self.current.get("summary", {})

        categories = set(baseline_summary.keys()) | set(current_summary.keys())
        categories.discard("overall")

        for category in sorted(categories):
            base_cat = baseline_summary.get(category, {})
            curr_cat = current_summary.get(category, {})

            if not base_cat and not curr_cat:
                continue

            lines.append(f"### {category.replace('_', ' ').title()}\n")
            lines.append("| Metric | Baseline | Current | Change |")
            lines.append("|--------|----------|---------|--------|")

            # Duration
            dur_change = self._calculate_change(
                base_cat.get("avg_duration_ms", 0),
                curr_cat.get("avg_duration_ms", 0)
            )
            lines.append(f"| Avg Duration | "
                        f"{self._format_value(dur_change['baseline'], 'ms')} | "
                        f"{self._format_value(dur_change['current'], 'ms')} | "
                        f"{self._format_change(dur_change)} |")

            # P95 Duration
            p95_change = self._calculate_change(
                base_cat.get("p95_duration_ms", 0),
                curr_cat.get("p95_duration_ms", 0)
            )
            lines.append(f"| P95 Duration | "
                        f"{self._format_value(p95_change['baseline'], 'ms')} | "
                        f"{self._format_value(p95_change['current'], 'ms')} | "
                        f"{self._format_change(p95_change)} |")

            # Total Tokens
            tokens_change = self._calculate_change(
                base_cat.get("total_tokens", 0),
                curr_cat.get("total_tokens", 0)
            )
            lines.append(f"| Total Tokens | "
                        f"{int(tokens_change['baseline'])} | "
                        f"{int(tokens_change['current'])} | "
                        f"{self._format_change(tokens_change)} |")

            # Cost
            cost_change = self._calculate_change(
                base_cat.get("total_cost_usd", 0),
                curr_cat.get("total_cost_usd", 0)
            )
            lines.append(f"| Cost | "
                        f"{self._format_value(cost_change['baseline'], 'usd')} | "
                        f"{self._format_value(cost_change['current'], 'usd')} | "
                        f"{self._format_change(cost_change)} |")

            # Success Rate
            success_change = self._calculate_change(
                base_cat.get("success_rate", 0),
                curr_cat.get("success_rate", 0),
                lower_is_better=False
            )
            lines.append(f"| Success Rate | "
                        f"{self._format_value(success_change['baseline'], '%')} | "
                        f"{self._format_value(success_change['current'], '%')} | "
                        f"{self._format_change(success_change)} |")

            lines.append("")

        return "\n".join(lines)

    def generate_test_results_table(self) -> str:
        """Generate individual test results table"""
        lines = []
        lines.append("## Individual Test Results\n")

        for category in ["rag_chat", "document_analysis", "risk_analysis"]:
            baseline_tests = self.baseline.get("results", {}).get(category, [])
            current_tests = self.current.get("results", {}).get(category, [])

            if not baseline_tests and not current_tests:
                continue

            lines.append(f"### {category.replace('_', ' ').title()}\n")
            lines.append("| Test | Baseline (ms) | Current (ms) | Change | Status |")
            lines.append("|------|---------------|--------------|--------|--------|")

            # Match tests by test_id
            baseline_dict = {t["test_id"]: t for t in baseline_tests}
            current_dict = {t["test_id"]: t for t in current_tests}

            all_ids = set(baseline_dict.keys()) | set(current_dict.keys())

            for test_id in sorted(all_ids):
                base_test = baseline_dict.get(test_id, {})
                curr_test = current_dict.get(test_id, {})

                test_name = base_test.get("test_name") or curr_test.get("test_name", test_id)
                base_dur = base_test.get("performance", {}).get("duration_ms", 0)
                curr_dur = curr_test.get("performance", {}).get("duration_ms", 0)

                dur_change = self._calculate_change(base_dur, curr_dur)

                base_status = base_test.get("response_data", {}).get("status", "N/A")
                curr_status = curr_test.get("response_data", {}).get("status", "N/A")

                status = "" if curr_status == "success" else ""

                lines.append(f"| {test_name} | "
                            f"{base_dur:.0f} | "
                            f"{curr_dur:.0f} | "
                            f"{self._format_change(dur_change)} | "
                            f"{status} |")

            lines.append("")

        return "\n".join(lines)

    def generate_system_info(self) -> str:
        """Generate system information section"""
        lines = []
        lines.append("## System Information\n")

        baseline_sys = self.baseline.get("metadata", {}).get("system", {})
        current_sys = self.current.get("metadata", {}).get("system", {})

        lines.append("### Baseline")
        lines.append(f"- Platform: {baseline_sys.get('platform', 'N/A')}")
        lines.append(f"- Python: {baseline_sys.get('python_version', 'N/A')}")
        lines.append(f"- CPU: {baseline_sys.get('cpu_count', 'N/A')} cores")
        lines.append(f"- Memory: {baseline_sys.get('total_memory_gb', 'N/A')} GB")
        lines.append(f"- Timestamp: {self.baseline.get('metadata', {}).get('timestamp', 'N/A')}")

        lines.append("")
        lines.append("### Current")
        lines.append(f"- Platform: {current_sys.get('platform', 'N/A')}")
        lines.append(f"- Python: {current_sys.get('python_version', 'N/A')}")
        lines.append(f"- CPU: {current_sys.get('cpu_count', 'N/A')} cores")
        lines.append(f"- Memory: {current_sys.get('total_memory_gb', 'N/A')} GB")
        lines.append(f"- Timestamp: {self.current.get('metadata', {}).get('timestamp', 'N/A')}")

        lines.append("")
        return "\n".join(lines)

    def generate_recommendations(self) -> str:
        """Generate recommendations based on results"""
        lines = []
        lines.append("## Recommendations\n")

        baseline_summary = self.baseline.get("summary", {}).get("overall", {})
        current_summary = self.current.get("summary", {}).get("overall", {})

        duration_change = self._calculate_change(
            baseline_summary.get("avg_duration_ms", 0),
            current_summary.get("avg_duration_ms", 0)
        )

        if duration_change["improved"]:
            improvement = abs(duration_change["change_pct"])
            if improvement > 30:
                lines.append("- **Significant performance improvement** detected. "
                            "The new implementation shows substantial benefits.")
            elif improvement > 10:
                lines.append("- **Moderate performance improvement** detected. "
                            "Consider deploying the new implementation.")
            else:
                lines.append("- **Minor performance improvement** detected. "
                            "Evaluate other factors before deciding.")
        else:
            regression = abs(duration_change["change_pct"])
            if regression > 20:
                lines.append("- **Warning: Significant performance regression** detected. "
                            "Investigate before deployment.")
            elif regression > 5:
                lines.append("- **Caution: Minor performance regression** detected. "
                            "Verify if the trade-off is acceptable.")

        # Success rate check
        success_change = self._calculate_change(
            baseline_summary.get("success_rate", 0),
            current_summary.get("success_rate", 0),
            lower_is_better=False
        )

        if current_summary.get("success_rate", 0) < 100:
            lines.append("- **Reliability**: Some tests are failing. "
                        "Investigate failed test cases before deployment.")

        # Cost check
        cost_change = self._calculate_change(
            baseline_summary.get("total_cost_usd", 0),
            current_summary.get("total_cost_usd", 0)
        )

        if cost_change["improved"] and abs(cost_change["change_pct"]) > 10:
            lines.append("- **Cost savings** detected. "
                        "The new implementation is more cost-effective.")

        lines.append("")
        return "\n".join(lines)

    def generate_report(self) -> str:
        """Generate complete comparison report"""
        baseline_mode = self.baseline.get("metadata", {}).get("mode", "unknown")
        current_mode = self.current.get("metadata", {}).get("mode", "unknown")

        report = []

        # Header
        report.append(f"# Performance Comparison Report")
        report.append(f"\n**{baseline_mode.upper()} vs {current_mode.upper()}**\n")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Sections
        report.append(self.generate_executive_summary())
        report.append(self.generate_detailed_comparison())
        report.append(self.generate_test_results_table())
        report.append(self.generate_recommendations())
        report.append(self.generate_system_info())

        return "\n".join(report)

    def save_report(self, output_path: str):
        """Save report to file"""
        report = self.generate_report()

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report)

        print(f"Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate performance comparison report"
    )
    parser.add_argument(
        "--baseline",
        required=True,
        help="Path to baseline results JSON"
    )
    parser.add_argument(
        "--current",
        required=True,
        help="Path to current results JSON"
    )
    parser.add_argument(
        "--output",
        default="reports/comparison_report.md",
        help="Output path for the report"
    )

    args = parser.parse_args()

    # Change to script directory
    import os
    os.chdir(Path(__file__).parent.parent)

    generator = ReportGenerator(args.baseline, args.current)
    generator.save_report(args.output)

    # Print summary to console
    print("\n" + "="*60)
    print("REPORT GENERATED")
    print("="*60)
    print(generator.generate_executive_summary())


if __name__ == "__main__":
    main()
