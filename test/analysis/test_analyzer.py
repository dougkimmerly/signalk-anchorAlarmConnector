#!/usr/bin/env python3
"""
Test Data Analyzer
Processes raw test data and produces scoring, phase detection, and recommendations
"""

import json
import os
import sys
import math
import statistics
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class TestAnalyzer:
    """Analyzes individual test results"""

    def __init__(self, test_data):
        self.data = test_data
        self.metadata = test_data.get('test_metadata', {})
        self.samples = test_data.get('samples', [])
        self.summary = test_data.get('summary', {})

    def detect_phases(self):
        """Detect deployment phases"""
        if not self.samples:
            return []

        phases = []
        current_phase = None
        phase_start = 0

        for i, sample in enumerate(self.samples):
            speed = sample.get('position', {}).get('speed', 0)

            # Simple phase detection
            if speed < 0.05:
                phase_type = 'STALLED'
            elif speed > 0.5:
                phase_type = 'ACCELERATION' if current_phase != 'ACCELERATION' else 'STEADY_STATE'
            else:
                phase_type = 'DECELERATION'

            if phase_type != current_phase:
                if current_phase:
                    phases.append({
                        'type': current_phase,
                        'start_sample': phase_start,
                        'end_sample': i,
                        'duration': sample['elapsed_sec'] - self.samples[phase_start]['elapsed_sec']
                    })
                current_phase = phase_type
                phase_start = i

        # Final phase
        if current_phase and self.samples:
            phases.append({
                'type': current_phase,
                'start_sample': phase_start,
                'end_sample': len(self.samples) - 1,
                'duration': self.samples[-1]['elapsed_sec'] - self.samples[phase_start]['elapsed_sec']
            })

        return phases

    def calculate_oscillation(self):
        """Calculate velocity oscillation metrics"""
        if len(self.samples) < 2:
            return {'frequency': 0, 'amplitude': 0, 'sign_changes': 0}

        speeds = [s.get('position', {}).get('speed', 0) for s in self.samples]

        # Count sign changes
        sign_changes = 0
        for i in range(1, len(speeds)):
            if speeds[i] * speeds[i-1] < 0:
                sign_changes += 1

        amplitude = max(speeds) - min(speeds) if speeds else 0
        frequency = sign_changes / (self.samples[-1]['elapsed_sec'] if self.samples else 1)

        return {
            'frequency': frequency,
            'amplitude': amplitude,
            'sign_changes': sign_changes,
            'score': self._oscillation_score(frequency, amplitude)
        }

    def _oscillation_score(self, frequency, amplitude):
        """Score oscillation (0-100, higher is better)"""
        if frequency < 0.1 and amplitude < 0.2:
            return 100
        elif frequency < 0.2 and amplitude < 0.5:
            return 80
        elif frequency < 0.5 and amplitude < 1.0:
            return 50
        else:
            return max(0, 100 - frequency * 50)

    def calculate_slack_management(self):
        """Analyze slack constraint compliance"""
        if not self.samples:
            return {'score': 0, 'negative_slack_time': 0, 'max_negative': 0}

        slack_values = []
        negative_count = 0

        for sample in self.samples:
            sim_state = sample.get('simulation_state', {})
            slack = sim_state.get('slack', 0)
            slack_values.append(slack)
            if slack < 0:
                negative_count += 1

        negative_time_pct = negative_count / len(self.samples) * 100 if self.samples else 0
        min_slack = min(slack_values) if slack_values else 0

        if negative_time_pct == 0:
            score = 100
        elif negative_time_pct < 5:
            score = 80
        elif negative_time_pct < 20:
            score = 50
        else:
            score = max(0, 100 - negative_time_pct)

        return {
            'score': score,
            'negative_slack_time_pct': negative_time_pct,
            'max_negative_slack': min_slack
        }

    def calculate_heading_stability(self):
        """Analyze heading stability after deployment"""
        if len(self.samples) < 180:  # Need last 90 seconds at 2Hz
            return {'score': 0, 'std_dev': 0, 'final_error': 0}

        # Last 180 samples (90 seconds at 2Hz)
        stable_samples = self.samples[-180:] if len(self.samples) > 180 else self.samples

        headings = [s.get('position', {}).get('heading', 0) for s in stable_samples]
        if not headings:
            return {'score': 0, 'std_dev': 0, 'final_error': 0}

        std_dev = statistics.stdev(headings) if len(headings) > 1 else 0

        # Get target bearing (should be toward anchor, approximately 0 for 180° wind)
        target_bearing = 0  # Toward north for south wind
        final_error = abs(headings[-1] - target_bearing)

        if std_dev < 5 and final_error < 10:
            score = 100
        elif std_dev < 10:
            score = 80
        elif std_dev < 20:
            score = 50
        else:
            score = 0

        return {
            'score': score,
            'std_dev': std_dev,
            'final_error': final_error
        }

    def calculate_motor_efficiency(self):
        """Analyze motor usage (for autoRetrieve tests)"""
        if self.metadata.get('test_type') != 'autoRetrieve':
            return None

        if not self.samples:
            return {'score': 0, 'duty_cycle': 0, 'engagements': 0}

        motor_on_time = 0
        last_motor_on = False
        engagements = 0

        for sample in self.samples:
            sim_state = sample.get('simulation_state', {})
            motor_force = sim_state.get('motor', {}).get('magnitude', 0)
            motor_on = motor_force > 10  # Consider on if > 10N

            if motor_on:
                motor_on_time += 0.5  # 500ms samples

            if motor_on and not last_motor_on:
                engagements += 1

            last_motor_on = motor_on

        total_time = self.samples[-1]['elapsed_sec'] if self.samples else 1
        duty_cycle = motor_on_time / total_time if total_time > 0 else 0

        # Motor should run 10-50% of time for efficient retrieval
        if 0.1 <= duty_cycle <= 0.5:
            score = 100
        elif duty_cycle < 0.1:
            score = 70  # Maybe needed more
        else:
            score = max(0, 100 - (duty_cycle - 0.5) * 100)

        return {
            'score': score,
            'duty_cycle': duty_cycle,
            'on_time_sec': motor_on_time,
            'total_time_sec': total_time,
            'engagements': engagements
        }

    def get_overall_score(self):
        """Calculate overall test score"""
        scores = {}

        # Oscillation (all tests)
        osc = self.calculate_oscillation()
        scores['oscillation'] = osc['score']

        # Slack management (all tests)
        slack = self.calculate_slack_management()
        scores['slack_management'] = slack['score']

        # Heading stability (all tests)
        heading = self.calculate_heading_stability()
        scores['heading_stability'] = heading['score']

        # Motor efficiency (autoRetrieve only)
        motor = self.calculate_motor_efficiency()
        if motor:
            scores['motor_efficiency'] = motor['score']

        # Scope achievement (autoDrop only)
        if self.metadata.get('test_type') == 'autoDrop':
            scope = self.summary.get('final_scope', 0)
            if scope >= 5.0:
                scores['scope_achievement'] = 100
            elif scope >= 4.0:
                scores['scope_achievement'] = 70
            else:
                scores['scope_achievement'] = max(0, scope * 20)

        # Rode retrieval (autoRetrieve only)
        if self.metadata.get('test_type') == 'autoRetrieve':
            rode = self.summary.get('final_rode', 0)
            if rode < 0.5:
                scores['rode_retrieval'] = 100
            elif rode < 2.0:
                scores['rode_retrieval'] = 80
            else:
                scores['rode_retrieval'] = max(0, 100 - rode * 10)

        # Completion (all tests)
        if self.samples:
            scores['completion'] = 100
        else:
            scores['completion'] = 0

        # Weighted average
        weights = {
            'completion': 0.20,
            'oscillation': 0.15,
            'slack_management': 0.15,
            'heading_stability': 0.10,
            'motor_efficiency': 0.15,
            'scope_achievement': 0.15,
            'rode_retrieval': 0.10
        }

        overall = 0
        weight_sum = 0
        for key, score in scores.items():
            if key in weights:
                weight = weights[key]
                overall += score * weight
                weight_sum += weight

        return {
            'overall': overall / weight_sum if weight_sum > 0 else 0,
            'components': scores,
            'weights': weights
        }


class DataAnalyzer:
    """Analyzes complete test session"""

    def __init__(self, session_dir):
        self.session_dir = Path(session_dir)
        self.raw_data_dir = self.session_dir / 'raw_data'
        self.analysis_dir = self.session_dir / 'analysis'
        self.tests = self._load_tests()

    def _load_tests(self):
        """Load all test files"""
        tests = []
        if not self.raw_data_dir.exists():
            return tests

        for test_file in sorted(self.raw_data_dir.glob('*.json')):
            try:
                with open(test_file) as f:
                    data = json.load(f)
                    tests.append(data)
            except:
                pass

        return tests

    def generate_summary(self):
        """Generate summary CSV"""
        summary_file = self.analysis_dir / 'test_summary.csv'

        with open(summary_file, 'w') as f:
            f.write('Test,Type,Wind_kn,Depth_m,Duration_sec,Final_Scope,Final_Rode,Score,Pass\n')

            for test in self.tests:
                meta = test.get('test_metadata', {})
                summary = test.get('summary', {})

                analyzer = TestAnalyzer(test)
                score_data = analyzer.get_overall_score()
                score = score_data['overall']
                passed = score >= 50

                f.write(f"{meta.get('test_number', 0)},{meta.get('test_type', '')},"
                       f"{meta.get('wind_speed_kn', 0)},{meta.get('depth_m', 0)},"
                       f"{meta.get('duration_sec', 0):.0f},"
                       f"{summary.get('final_scope', 0):.1f},"
                       f"{summary.get('final_rode', 0):.1f},"
                       f"{score:.1f},"
                       f"{'PASS' if passed else 'FAIL'}\n")

        return summary_file

    def generate_recommendations(self):
        """Generate recommendations based on analysis"""
        rec_file = self.analysis_dir / 'RECOMMENDATIONS.md'

        passed_count = sum(1 for t in self.tests if len(t.get('samples', [])) > 0)
        failed_count = len(self.tests) - passed_count

        with open(rec_file, 'w') as f:
            f.write('# Overnight Test Recommendations\n\n')
            f.write(f'## Summary\n')
            f.write(f'- Total Tests: {len(self.tests)}\n')
            f.write(f'- Passed: {passed_count}\n')
            f.write(f'- Failed: {failed_count}\n')
            f.write(f'- Pass Rate: {passed_count/len(self.tests)*100:.1f}%\n\n')

            # Group by issue
            issues = defaultdict(list)
            for test in self.tests:
                meta = test.get('test_metadata', {})
                if len(test.get('samples', [])) == 0:
                    key = f"No data (wind={meta.get('wind_speed_kn')}kn, depth={meta.get('depth_m')}m)"
                    issues[key].append(test)
                else:
                    analyzer = TestAnalyzer(test)
                    oscillation = analyzer.calculate_oscillation()
                    if oscillation['frequency'] > 0.5:
                        key = f"High oscillation (freq={oscillation['frequency']:.2f}Hz)"
                        issues[key].append(test)

            if issues:
                f.write(f'## Issues Found\n\n')
                for issue, tests_with_issue in sorted(issues.items()):
                    f.write(f'### {issue}\n')
                    f.write(f'Affected: {len(tests_with_issue)} tests\n')
                    for test in tests_with_issue[:3]:
                        meta = test.get('test_metadata', {})
                        f.write(f'  - {meta.get("test_type")} @ {meta.get("wind_speed_kn")}kn, {meta.get("depth_m")}m\n')
                    f.write('\n')

            f.write(f'## Recommendations\n\n')
            f.write('1. Review low-wind performance (< 8kn) - may need motor assist\n')
            f.write('2. Check heading stability in high winds (> 18kn)\n')
            f.write('3. Verify deep water deployments (> 18m) complete within timeout\n')

        return rec_file


def main():
    """Analyze test session"""
    if len(sys.argv) < 2:
        print('Usage: python3 test_analyzer.py <session_directory>')
        sys.exit(1)

    session_dir = Path(sys.argv[1])
    if not session_dir.exists():
        print(f'Error: Session directory not found: {session_dir}')
        sys.exit(1)

    analyzer = DataAnalyzer(session_dir)

    print(f'Analyzing {len(analyzer.tests)} tests...')
    summary = analyzer.generate_summary()
    print(f'✓ Summary: {summary}')

    recommendations = analyzer.generate_recommendations()
    print(f'✓ Recommendations: {recommendations}')


if __name__ == '__main__':
    main()
