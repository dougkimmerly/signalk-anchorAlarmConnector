#!/usr/bin/env python3
"""
Test Results Analysis and Visualization

Analyzes logged test data to validate physics parameters and
identify areas needing tuning.
"""

import json
import csv
import math
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class PhysicsAnalyzer:
    """Analyzes test data to validate physics behavior"""

    def __init__(self, data: List[Dict]):
        """Initialize with test data"""
        self.data = data
        self.metrics = {}

    def calculate_drift_rate(self) -> Optional[float]:
        """
        Calculate average drift rate (distance change per second)

        Expected: ~0.8 m/s during anchor drop with 12kn wind
        """
        if len(self.data) < 2:
            return None

        distances = [point.get('distance', 0) for point in self.data]
        timestamps = [point.get('timestamp', 0) for point in self.data]

        if timestamps[-1] == timestamps[0]:
            return None

        total_distance = distances[-1] - distances[0]
        total_time = (timestamps[-1] - timestamps[0]) / 1000  # Convert ms to seconds

        if total_time == 0:
            return None

        return total_distance / total_time

    def calculate_heading_changes(self) -> Dict:
        """
        Analyze heading transitions

        Returns metrics on heading behavior at different rode lengths
        """
        heading_by_rode = {}

        for point in self.data:
            rode = point.get('rodeDeployed', 0)
            heading = point.get('heading', 0)

            # Bucket rode length in 5m increments
            rode_bucket = round(rode / 5) * 5

            if rode_bucket not in heading_by_rode:
                heading_by_rode[rode_bucket] = []

            heading_by_rode[rode_bucket].append(heading)

        # Calculate average heading for each bucket
        summary = {}
        for rode_bucket in sorted(heading_by_rode.keys()):
            headings = heading_by_rode[rode_bucket]
            avg_heading = mean(headings)
            heading_std = stdev(headings) if len(headings) > 1 else 0

            summary[rode_bucket] = {
                'average': avg_heading,
                'stdev': heading_std,
                'samples': len(headings)
            }

        return summary

    def calculate_max_distance(self) -> float:
        """Calculate maximum distance from anchor reached during test"""
        distances = [point.get('distance', 0) for point in self.data]
        return max(distances) if distances else 0

    def calculate_catenary_limit(self) -> Optional[float]:
        """
        Calculate theoretical maximum distance (catenary limit)
        for the rode deployed

        Catenary: max_distance = sqrt(rode² - (depth + bowHeight)²)
        """
        if not self.data:
            return None

        # Get rode at end of test
        final_rode = self.data[-1].get('rodeDeployed', 0)

        # Estimate depth and bow height from data
        # (these would normally be provided separately)
        depth = 5  # Default test depth
        bow_height = 2  # Default bow height

        vertical_rode = depth + bow_height
        if final_rode <= vertical_rode:
            return 0

        return math.sqrt(final_rode ** 2 - vertical_rode ** 2)

    def check_catenary_violation(self) -> List[int]:
        """
        Identify any points where boat exceeded catenary limit

        Returns list of indices where violation occurred
        """
        violations = []

        for i, point in enumerate(self.data):
            rode = point.get('rodeDeployed', 0)
            distance = point.get('distance', 0)

            depth = 5
            bow_height = 2
            vertical_rode = depth + bow_height

            if rode > vertical_rode:
                catenary_limit = math.sqrt(rode ** 2 - vertical_rode ** 2)
                if distance > catenary_limit * 1.01:  # Allow 1% tolerance
                    violations.append(i)

        return violations

    def calculate_slack_changes(self) -> Dict:
        """
        Analyze chain slack behavior

        Returns statistics on slack progression
        """
        slacks = [point.get('chainSlack', 0) for point in self.data]

        if not slacks:
            return {}

        return {
            'min_slack': min(slacks),
            'max_slack': max(slacks),
            'avg_slack': mean(slacks),
            'slack_range': max(slacks) - min(slacks),
            'went_negative': any(s < 0 for s in slacks),
            'negative_count': sum(1 for s in slacks if s < 0)
        }

    def calculate_velocity(self) -> Dict:
        """
        Calculate boat velocity statistics

        Returns speed and direction metrics
        """
        velocities = []

        for point in self.data:
            vx = point.get('velocityX', 0)
            vy = point.get('velocityY', 0)
            speed = math.sqrt(vx ** 2 + vy ** 2)
            velocities.append(speed)

        if not velocities:
            return {}

        return {
            'max_velocity': max(velocities),
            'avg_velocity': mean(velocities),
            'velocity_stdev': stdev(velocities) if len(velocities) > 1 else 0,
            'max_acceleration': self._calculate_max_acceleration()
        }

    def _calculate_max_acceleration(self) -> float:
        """Calculate maximum acceleration from velocity changes"""
        if len(self.data) < 2:
            return 0

        max_accel = 0
        dt = 0.5  # Simulation time step in seconds

        for i in range(1, len(self.data)):
            vx_prev = self.data[i-1].get('velocityX', 0)
            vy_prev = self.data[i-1].get('velocityY', 0)
            v_prev = math.sqrt(vx_prev ** 2 + vy_prev ** 2)

            vx_curr = self.data[i].get('velocityX', 0)
            vy_curr = self.data[i].get('velocityY', 0)
            v_curr = math.sqrt(vx_curr ** 2 + vy_curr ** 2)

            accel = abs(v_curr - v_prev) / dt
            max_accel = max(max_accel, accel)

        return max_accel

    def generate_report(self) -> str:
        """Generate a comprehensive analysis report"""
        report = []
        report.append("=" * 70)
        report.append("PHYSICS ANALYSIS REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Data points: {len(self.data)}")
        report.append("")

        # Drift analysis
        report.append("DRIFT ANALYSIS")
        report.append("-" * 70)
        drift_rate = self.calculate_drift_rate()
        if drift_rate is not None:
            report.append(f"Average drift rate: {drift_rate:.3f} m/s")
            if 0.6 <= drift_rate <= 1.0:
                report.append("✓ Drift rate is within expected range (0.6-1.0 m/s)")
            else:
                report.append(f"✗ Drift rate is out of range (expected 0.6-1.0 m/s)")
        report.append("")

        # Distance and catenary
        report.append("DISTANCE AND CATENARY")
        report.append("-" * 70)
        max_dist = self.calculate_max_distance()
        catenary_limit = self.calculate_catenary_limit()
        report.append(f"Maximum distance from anchor: {max_dist:.2f} m")
        if catenary_limit is not None:
            report.append(f"Catenary limit: {catenary_limit:.2f} m")
            if max_dist <= catenary_limit * 1.01:
                report.append("✓ Distance respects catenary limit")
            else:
                report.append(f"✗ Distance exceeds catenary limit by {max_dist - catenary_limit:.2f} m")
        report.append("")

        # Catenary violations
        violations = self.check_catenary_violation()
        if violations:
            report.append(f"✗ Catenary violations at {len(violations)} points")
            for idx in violations[:5]:  # Show first 5
                point = self.data[idx]
                report.append(f"  - At t={point.get('timestamp', 0)}ms: "
                            f"distance={point.get('distance', 0):.2f}m, "
                            f"rode={point.get('rodeDeployed', 0):.2f}m")
        else:
            report.append("✓ No catenary violations detected")
        report.append("")

        # Slack analysis
        report.append("CHAIN SLACK ANALYSIS")
        report.append("-" * 70)
        slack_stats = self.calculate_slack_changes()
        if slack_stats:
            report.append(f"Min slack: {slack_stats['min_slack']:.2f} m")
            report.append(f"Max slack: {slack_stats['max_slack']:.2f} m")
            report.append(f"Avg slack: {slack_stats['avg_slack']:.2f} m")
            if slack_stats['went_negative']:
                report.append(f"✗ Slack went negative {slack_stats['negative_count']} times")
            else:
                report.append("✓ Slack remained non-negative throughout test")
        report.append("")

        # Heading analysis
        report.append("HEADING ANALYSIS")
        report.append("-" * 70)
        heading_summary = self.calculate_heading_changes()
        for rode_bucket in sorted(heading_summary.keys()):
            stats = heading_summary[rode_bucket]
            report.append(f"Rode ~{rode_bucket}m: heading={stats['average']:.1f}° "
                        f"(±{stats['stdev']:.1f}°, n={stats['samples']})")
        report.append("")

        # Velocity analysis
        report.append("VELOCITY ANALYSIS")
        report.append("-" * 70)
        vel_stats = self.calculate_velocity()
        if vel_stats:
            report.append(f"Max velocity: {vel_stats['max_velocity']:.3f} m/s")
            report.append(f"Avg velocity: {vel_stats['avg_velocity']:.3f} m/s")
            report.append(f"Max acceleration: {vel_stats['max_acceleration']:.3f} m/s²")
        report.append("")

        report.append("=" * 70)

        return "\n".join(report)

    def export_csv(self, filename: str):
        """Export data to CSV for external analysis"""
        if not self.data:
            logger.warning("No data to export")
            return

        try:
            fieldnames = list(self.data[0].keys())

            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.data)

            logger.info(f"Data exported to {filename}")
        except IOError as e:
            logger.error(f"Error exporting CSV: {e}")


def main():
    """Main entry point for analysis"""
    import sys

    if len(sys.argv) < 2:
        logger.error("Usage: python3 analyze_results.py <data_file.json>")
        sys.exit(1)

    data_file = sys.argv[1]

    try:
        with open(data_file, 'r') as f:
            test_data = json.load(f)

        # Extract data points (handle both direct array and nested format)
        if isinstance(test_data, list):
            data = test_data
        elif isinstance(test_data, dict) and 'data' in test_data:
            data = test_data['data']
        else:
            logger.error("Invalid data format")
            sys.exit(1)

        analyzer = PhysicsAnalyzer(data)

        # Generate and print report
        report = analyzer.generate_report()
        print(report)

        # Export to CSV
        csv_file = data_file.replace('.json', '.csv')
        analyzer.export_csv(csv_file)

    except FileNotFoundError:
        logger.error(f"File not found: {data_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {data_file}")
        sys.exit(1)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main()
