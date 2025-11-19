#!/usr/bin/env python3
"""
Analyze conversation patterns to detect if an agent is stuck.
This can be run periodically to auto-detect stuck conditions.
"""

import json
import sys
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple

class StuckPatternAnalyzer:
    """Analyzes conversation history for patterns indicating the agent is stuck."""

    def __init__(self, history_file: Path = None):
        self.history_file = history_file or Path.home() / '.claude' / 'history.jsonl'
        self.stuck_patterns = []
        self.session_data = []

    def load_current_session(self) -> List[Dict]:
        """Load messages from the current session."""
        if not self.history_file.exists():
            return []

        messages = []
        with open(self.history_file, 'r') as f:
            lines = f.readlines()
            if not lines:
                return []

            # Get the last session ID
            last_entry = json.loads(lines[-1])
            session_id = last_entry.get('sessionId')

            # Collect all messages from this session
            for line in lines:
                entry = json.loads(line)
                if entry.get('sessionId') == session_id:
                    messages.append(entry)

        return messages

    def analyze_patterns(self) -> Dict:
        """Analyze the session for stuck patterns."""
        self.session_data = self.load_current_session()

        if not self.session_data:
            return {"stuck": False, "reason": "No session data found"}

        results = {
            "stuck": False,
            "confidence": 0,
            "patterns_detected": [],
            "metrics": {},
            "recommendations": []
        }

        # Check various patterns
        self._check_time_on_task(results)
        self._check_repetitive_errors(results)
        self._check_test_timeouts(results)
        self._check_killshell_usage(results)
        self._check_approach_changes(results)
        self._check_self_awareness(results)
        self._check_compilation_loops(results)

        # Calculate overall stuck confidence
        confidence = len(results["patterns_detected"]) * 20
        confidence = min(confidence, 100)
        results["confidence"] = confidence

        # Determine if stuck (threshold: 60% confidence or critical patterns)
        critical_patterns = ["multiple_test_timeouts", "excessive_killshell", "explicitly_stuck"]
        has_critical = any(p in [pattern.split(":")[0] for pattern in results["patterns_detected"]]
                          for p in critical_patterns)

        results["stuck"] = confidence >= 60 or has_critical

        # Add recommendations
        if results["stuck"]:
            results["recommendations"] = self._generate_recommendations(results)

        return results

    def _check_time_on_task(self, results: Dict):
        """Check if too much time spent on the same task."""
        if not self.session_data:
            return

        first_timestamp = self.session_data[0].get('timestamp', 0)
        last_timestamp = self.session_data[-1].get('timestamp', 0)

        duration_ms = last_timestamp - first_timestamp
        duration_minutes = duration_ms / (1000 * 60)

        results["metrics"]["session_duration_minutes"] = round(duration_minutes, 1)

        # Look for patterns indicating same problem for extended time
        if duration_minutes > 15:
            # Check if still working on same error
            error_messages = self._extract_error_patterns()
            if error_messages and len(set(error_messages)) <= 3:
                results["patterns_detected"].append(f"same_errors_for_{int(duration_minutes)}_minutes")

    def _check_repetitive_errors(self, results: Dict):
        """Check for repetitive error messages."""
        error_patterns = self._extract_error_patterns()

        if error_patterns:
            error_counts = {}
            for error in error_patterns:
                error_counts[error] = error_counts.get(error, 0) + 1

            # Find errors that repeat too often
            repetitive = [(e, c) for e, c in error_counts.items() if c >= 3]
            if repetitive:
                results["metrics"]["repetitive_errors"] = repetitive
                for error, count in repetitive:
                    results["patterns_detected"].append(f"error_repeated_{count}_times: {error[:50]}")

    def _check_test_timeouts(self, results: Dict):
        """Check for test timeout patterns."""
        timeout_count = 0
        hanging_patterns = [
            r"test.*hang",
            r"timeout.*test",
            r"Still waiting",
            r"Checking.*test.*status",
            r"test.*running.*\d+.*seconds"
        ]

        for msg in self.session_data:
            display = msg.get('display', '').lower()
            for pattern in hanging_patterns:
                if re.search(pattern, display, re.IGNORECASE):
                    timeout_count += 1
                    break

        if timeout_count >= 3:
            results["metrics"]["test_timeouts"] = timeout_count
            results["patterns_detected"].append(f"multiple_test_timeouts: {timeout_count}")

    def _check_killshell_usage(self, results: Dict):
        """Check for excessive KillShell command usage."""
        kill_count = sum(1 for msg in self.session_data
                        if 'KillShell' in msg.get('display', ''))

        if kill_count >= 3:
            results["metrics"]["killshell_count"] = kill_count
            results["patterns_detected"].append(f"excessive_killshell: {kill_count}")

    def _check_approach_changes(self, results: Dict):
        """Check for multiple approach changes indicating confusion."""
        approach_indicators = [
            r"try.*different.*approach",
            r"let me.*instead",
            r"actually.*better",
            r"scratch that",
            r"nevermind",
            r"different.*strategy"
        ]

        approach_changes = 0
        for msg in self.session_data:
            display = msg.get('display', '').lower()
            for pattern in approach_indicators:
                if re.search(pattern, display, re.IGNORECASE):
                    approach_changes += 1
                    break

        if approach_changes >= 3:
            results["metrics"]["approach_changes"] = approach_changes
            results["patterns_detected"].append(f"multiple_approach_changes: {approach_changes}")

    def _check_self_awareness(self, results: Dict):
        """Check for self-aware statements about being stuck."""
        stuck_phrases = [
            r"overcomplicating",
            r"this.*isn't working",
            r"stuck",
            r"can't.*figure.*out",
            r"keep.*getting.*same.*error",
            r"tried.*multiple.*times"
        ]

        for msg in self.session_data:
            display = msg.get('display', '')
            for phrase in stuck_phrases:
                if re.search(phrase, display, re.IGNORECASE):
                    results["patterns_detected"].append(f"explicitly_stuck: {phrase}")
                    return

    def _check_compilation_loops(self, results: Dict):
        """Check for compile-fix-compile loops."""
        compile_commands = sum(1 for msg in self.session_data
                              if re.search(r'cargo (check|build|test)', msg.get('display', '')))

        if compile_commands >= 10:
            results["metrics"]["compilation_attempts"] = compile_commands
            results["patterns_detected"].append(f"compilation_loop: {compile_commands}_attempts")

    def _extract_error_patterns(self) -> List[str]:
        """Extract error message patterns from the conversation."""
        errors = []
        error_indicators = [
            r'error\[.*?\]:',
            r'error:',
            r'panic',
            r'failed',
            r'cannot.*',
            r'unable to.*'
        ]

        for msg in self.session_data:
            display = msg.get('display', '')
            for indicator in error_indicators:
                matches = re.findall(indicator + r'.*', display, re.IGNORECASE)
                errors.extend(matches[:1])  # Take first match per message

        return errors

    def _generate_recommendations(self, results: Dict) -> List[str]:
        """Generate recommendations based on detected patterns."""
        recommendations = []

        if "multiple_test_timeouts" in str(results["patterns_detected"]):
            recommendations.append("Tests are consistently timing out - likely an async/await or threading issue")

        if "excessive_killshell" in str(results["patterns_detected"]):
            recommendations.append("Frequent process killing suggests infinite loops or deadlocks")

        if "compilation_loop" in str(results["patterns_detected"]):
            recommendations.append("Stuck in compile-fix cycle - may need architectural redesign")

        if "multiple_approach_changes" in str(results["patterns_detected"]):
            recommendations.append("Multiple approach changes indicate fundamental misunderstanding")

        if results["confidence"] >= 80:
            recommendations.append("HIGH CONFIDENCE: Immediate escalation recommended")

        return recommendations


def main():
    """Main entry point for the analyzer."""
    analyzer = StuckPatternAnalyzer()
    results = analyzer.analyze_patterns()

    print("=" * 60)
    print("STUCK PATTERN ANALYSIS REPORT")
    print("=" * 60)
    print()

    if results["stuck"]:
        print("⚠️  STATUS: STUCK DETECTED")
        print(f"Confidence: {results['confidence']}%")
    else:
        print("✅ STATUS: Not stuck")
        print(f"Confidence: {results['confidence']}%")

    print()
    print("Patterns Detected:")
    for pattern in results["patterns_detected"]:
        print(f"  • {pattern}")

    if results["metrics"]:
        print()
        print("Metrics:")
        for key, value in results["metrics"].items():
            print(f"  • {key}: {value}")

    if results["recommendations"]:
        print()
        print("Recommendations:")
        for rec in results["recommendations"]:
            print(f"  • {rec}")

    print()
    print("-" * 60)

    # Return exit code based on stuck status
    sys.exit(1 if results["stuck"] else 0)


if __name__ == "__main__":
    main()