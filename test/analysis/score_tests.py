#!/usr/bin/env python3
"""
Test Scoring System
Evaluates each autoDrop test against expected windvane behavior goals.
Tracks progress over multiple test runs with detailed breakdown.
"""

import json
import glob
import csv
from datetime import datetime
from pathlib import Path
import os

# Target metrics
TARGET_HEADING = 180.0        # Degrees - boat should point into wind (from South)
HEADING_TOLERANCE = 20.0      # ±20° is acceptable
TARGET_MOVEMENT = 0.0         # Degrees - boat should move North (away from South wind)
MOVEMENT_TOLERANCE = 30.0     # ±30° is acceptable
TARGET_SCOPE = 5.0            # 5:1 scope ratio
MIN_SCOPE = 4.5               # Minimum acceptable scope
TARGET_FINAL_RODE = 15.0      # Meters - should deploy 15m for 3m depth
MIN_RODE_DEPLOYED = 12.0      # Minimum acceptable rode

class TestScorer:
    def __init__(self, test_file):
        self.test_file = test_file
        self.data = self.load_test_data()
        self.scores = {}

    def load_test_data(self):
        """Load JSON test data"""
        try:
            with open(self.test_file, 'r') as f:
                return json.load(f)
        except:
            return None

    def score_heading_accuracy(self):
        """Score how well boat heading matches target (180°)"""
        if not self.data or 'samples' not in self.data:
            return 0, "No samples data"

        samples = self.data['samples']
        if not samples:
            return 0, "Empty samples"

        # Analyze heading during middle and final phases (after wind fully effects boat)
        # Skip first 5 seconds to let dynamics settle
        stable_samples = [s for s in samples if s.get('time_sec', 0) >= 5]

        if not stable_samples:
            return 0, "No stable samples after 5s"

        headings = [s['boat_heading'] for s in stable_samples if s.get('boat_heading') is not None]
        if not headings:
            return 0, "No heading data"

        avg_heading = sum(headings) / len(headings)

        # Calculate error from target
        heading_error = abs(avg_heading - TARGET_HEADING)
        if heading_error > 180:
            heading_error = 360 - heading_error

        # Scoring: 100 if perfect, 0 if off by >60°
        if heading_error <= HEADING_TOLERANCE:
            score = 100
        else:
            score = max(0, 100 - (heading_error - HEADING_TOLERANCE) * 2)

        detail = f"Avg heading={avg_heading:.1f}° (target={TARGET_HEADING}°, error={heading_error:.1f}°)"
        return score, detail

    def score_movement_direction(self):
        """Score how well boat moves in correct direction (North, 0°)"""
        if not self.data or 'samples' not in self.data:
            return 0, "No samples data"

        samples = self.data['samples']
        if len(samples) < 2:
            return 0, "Not enough samples"

        # Calculate movement vector from first to last position
        first = samples[0]
        last = samples[-1]

        lat_change = (last.get('latitude', 0) or 0) - (first.get('latitude', 0) or 0)
        lon_change = (last.get('longitude', 0) or 0) - (first.get('longitude', 0) or 0)

        if lat_change == 0 and lon_change == 0:
            return 0, "No movement detected"

        # Calculate bearing of movement (0=North, 90=East, 180=South, 270=West)
        import math
        movement_bearing = math.atan2(lon_change, lat_change) * 180 / math.pi
        if movement_bearing < 0:
            movement_bearing += 360

        # Should be moving North (0-30° or 330-360°)
        movement_error = min(movement_bearing, 360 - movement_bearing)

        # Scoring: 100 if perfect North movement, 0 if moving South
        if movement_error <= MOVEMENT_TOLERANCE:
            score = 100
        else:
            score = max(0, 100 - (movement_error - MOVEMENT_TOLERANCE) * 1.5)

        detail = f"Movement bearing={movement_bearing:.1f}° (target=0°, error={movement_error:.1f}°)"
        return score, detail

    def score_negative_scope(self):
        """Score % of readings that had negative scope (impossible physics)"""
        if not self.data or 'samples' not in self.data:
            return 100, "No samples data"

        samples = self.data['samples']
        if not samples:
            return 100, "Empty samples"

        negative_count = 0
        for sample in samples:
            rode = sample.get('rode_deployed', 0)
            depth = sample.get('depth', 3.0)
            if depth <= 0:
                depth = 3.0
            scope = rode / (depth + 2.0)  # 2.0m bow height
            if scope < 0:
                negative_count += 1

        negative_pct = (negative_count / len(samples)) * 100 if samples else 0

        # Scoring: 100 if 0% negative, penalize heavily for any negative scopes
        if negative_pct == 0:
            score = 100
        else:
            score = max(0, 100 - (negative_pct * 2))  # Lose 2 points per percent

        detail = f"Negative scope: {negative_count}/{len(samples)} ({negative_pct:.1f}%)"
        return score, detail

    def score_scope_achieved(self):
        """Score final scope reached"""
        if not self.data:
            return 0, "No test data"

        final_scope = self.data.get('final_scope', 0)
        final_rode = self.data.get('final_rode', 0)

        if final_scope >= TARGET_SCOPE:
            score = 100
            detail = f"Scope={final_scope:.2f}:1 (target={TARGET_SCOPE}:1) ✓"
        elif final_scope >= MIN_SCOPE:
            pct = (final_scope / TARGET_SCOPE) * 100
            score = 70 + (pct - 90)
            detail = f"Scope={final_scope:.2f}:1 (target={TARGET_SCOPE}:1, {pct:.0f}%)"
        elif final_rode >= MIN_RODE_DEPLOYED:
            score = 50 + (final_rode / TARGET_FINAL_RODE) * 25
            detail = f"Rode={final_rode:.1f}m (target={TARGET_FINAL_RODE}m)"
        else:
            score = (final_rode / MIN_RODE_DEPLOYED) * 40
            detail = f"Rode={final_rode:.1f}m (minimum={MIN_RODE_DEPLOYED}m)"

        return max(0, min(100, score)), detail

    def score_deployment_length(self):
        """Score total rode deployed"""
        if not self.data:
            return 0, "No test data"

        final_rode = self.data.get('final_rode', 0)

        if final_rode >= TARGET_FINAL_RODE:
            score = 100
            detail = f"Rode={final_rode:.1f}m ✓"
        elif final_rode >= MIN_RODE_DEPLOYED:
            score = 75 + (final_rode - MIN_RODE_DEPLOYED) * 5
            detail = f"Rode={final_rode:.1f}m (target={TARGET_FINAL_RODE}m)"
        else:
            score = (final_rode / MIN_RODE_DEPLOYED) * 50
            detail = f"Rode={final_rode:.1f}m (minimum={MIN_RODE_DEPLOYED}m)"

        return max(0, min(100, score)), detail

    def score_stability(self):
        """Score motion stability (how smooth deployment is)"""
        if not self.data or 'samples' not in self.data:
            return 0, "No samples data"

        samples = self.data['samples']
        if len(samples) < 2:
            return 0, "Not enough samples"

        # Track speed variations
        speeds = []
        for s in samples:
            if 'boat_speed' in s and s['boat_speed'] is not None:
                speeds.append(s['boat_speed'] * 1.94384)  # Convert m/s to knots

        if not speeds or len(speeds) < 2:
            return 50, "Limited speed data"

        # Calculate speed standard deviation
        avg_speed = sum(speeds) / len(speeds)
        variance = sum((s - avg_speed) ** 2 for s in speeds) / len(speeds)
        std_dev = variance ** 0.5

        # Count speed spikes (>50% variation from mean)
        spike_threshold = avg_speed * 1.5
        spikes = sum(1 for s in speeds if s > spike_threshold)
        spike_pct = (spikes / len(speeds)) * 100 if speeds else 0

        # Scoring: fewer spikes is better
        if spike_pct < 5:
            score = 100
        elif spike_pct < 15:
            score = 90
        elif spike_pct < 25:
            score = 70
        else:
            score = max(0, 50 - spike_pct)

        detail = f"Speed std_dev={std_dev:.2f}kt, spikes={spikes}/{len(speeds)} ({spike_pct:.0f}%)"
        return score, detail

    def calculate_overall_score(self):
        """Calculate weighted overall score"""
        heading_score, heading_detail = self.score_heading_accuracy()
        movement_score, movement_detail = self.score_movement_direction()
        scope_score, scope_detail = self.score_scope_achieved()
        deployment_score, deployment_detail = self.score_deployment_length()
        stability_score, stability_detail = self.score_stability()
        negative_scope_score, negative_scope_detail = self.score_negative_scope()

        # Weights (should sum to 100)
        weights = {
            'heading': 25,      # Critical for windvaning behavior
            'movement': 25,     # Critical for proper physics
            'scope': 25,        # Main goal of autoDrop
            'deployment': 15,   # Rode length indicator
            'stability': 5,     # Smoothness of operation
            'negative_scope': 5, # Physics validity
        }

        overall = (
            heading_score * weights['heading'] +
            movement_score * weights['movement'] +
            scope_score * weights['scope'] +
            deployment_score * weights['deployment'] +
            stability_score * weights['stability'] +
            negative_scope_score * weights['negative_scope']
        ) / 100

        self.scores = {
            'timestamp': Path(self.test_file).stem,
            'heading': heading_score,
            'movement': movement_score,
            'scope': scope_score,
            'deployment': deployment_score,
            'stability': stability_score,
            'negative_scope': negative_scope_score,
            'overall': overall,
            'details': {
                'heading': heading_detail,
                'movement': movement_detail,
                'scope': scope_detail,
                'deployment': deployment_detail,
                'stability': stability_detail,
                'negative_scope': negative_scope_detail,
            }
        }

        return self.scores

    def print_detailed_report(self):
        """Print detailed test report"""
        if not self.scores:
            self.calculate_overall_score()

        print(f"\n{'='*70}")
        print(f"TEST REPORT: {self.scores['timestamp']}")
        print(f"{'='*70}")
        print(f"\nScore Breakdown:")
        print(f"  Heading Accuracy:     {self.scores['heading']:6.1f}/100  - {self.scores['details']['heading']}")
        print(f"  Movement Direction:   {self.scores['movement']:6.1f}/100  - {self.scores['details']['movement']}")
        print(f"  Scope Achieved:       {self.scores['scope']:6.1f}/100  - {self.scores['details']['scope']}")
        print(f"  Deployment Length:    {self.scores['deployment']:6.1f}/100  - {self.scores['details']['deployment']}")
        print(f"  Motion Stability:     {self.scores['stability']:6.1f}/100  - {self.scores['details']['stability']}")
        print(f"  Physics Validity:     {self.scores['negative_scope']:6.1f}/100  - {self.scores['details']['negative_scope']}")
        print(f"\n  OVERALL SCORE:        {self.scores['overall']:6.1f}/100")
        print(f"{'='*70}\n")

def score_all_tests():
    """Score all autoDrop test files and generate report"""
    test_files = sorted(glob.glob('autodrop_15kn*.json'))

    if not test_files:
        print("No test files found (autodrop_15kn*.json)")
        return

    print(f"\nScoring {len(test_files)} test files...\n")

    all_scores = []

    for test_file in test_files:
        scorer = TestScorer(test_file)
        scores = scorer.calculate_overall_score()
        all_scores.append(scores)
        scorer.print_detailed_report()

    # Generate summary table
    print("\n" + "="*90)
    print("OVERALL PROGRESS TABLE")
    print("="*90)
    print(f"{'Test':<20} {'Overall':>8} {'Heading':>8} {'Movement':>8} {'Scope':>8} {'Deploy':>8} {'Stable':>8}")
    print("-"*90)

    for scores in all_scores:
        print(f"{scores['timestamp']:<20} {scores['overall']:>8.1f} {scores['heading']:>8.1f} "
              f"{scores['movement']:>8.1f} {scores['scope']:>8.1f} {scores['deployment']:>8.1f} {scores['stability']:>8.1f}")

    # Calculate averages and trends
    avg_overall = sum(s['overall'] for s in all_scores) / len(all_scores)
    avg_heading = sum(s['heading'] for s in all_scores) / len(all_scores)
    avg_movement = sum(s['movement'] for s in all_scores) / len(all_scores)
    avg_scope = sum(s['scope'] for s in all_scores) / len(all_scores)
    avg_deployment = sum(s['deployment'] for s in all_scores) / len(all_scores)
    avg_stability = sum(s['stability'] for s in all_scores) / len(all_scores)

    print("-"*90)
    print(f"{'AVERAGE':<20} {avg_overall:>8.1f} {avg_heading:>8.1f} "
          f"{avg_movement:>8.1f} {avg_scope:>8.1f} {avg_deployment:>8.1f} {avg_stability:>8.1f}")
    print("="*90)

    # Find biggest failure area
    print(f"\nBiggest Opportunities for Improvement:")
    areas = [
        ('Heading Accuracy', avg_heading),
        ('Movement Direction', avg_movement),
        ('Scope Achievement', avg_scope),
        ('Rode Deployment', avg_deployment),
        ('Motion Stability', avg_stability),
    ]
    areas_sorted = sorted(areas, key=lambda x: x[1])

    for i, (area, score) in enumerate(areas_sorted[:3], 1):
        print(f"  {i}. {area:25s}: {score:6.1f}/100")

    print(f"\nOverall Progress: {avg_overall:.1f}/100\n")

    # Save summary to CSV
    csv_file = 'test_scores_history.csv'
    with open(csv_file, 'a', newline='') as f:
        writer = csv.writer(f)
        # Write header if file is empty
        if os.path.getsize(csv_file) == 0 if os.path.exists(csv_file) else True:
            writer.writerow(['Test', 'Overall', 'Heading', 'Movement', 'Scope', 'Deployment', 'Stability'])
        # Write scores
        for scores in all_scores:
            writer.writerow([
                scores['timestamp'],
                f"{scores['overall']:.1f}",
                f"{scores['heading']:.1f}",
                f"{scores['movement']:.1f}",
                f"{scores['scope']:.1f}",
                f"{scores['deployment']:.1f}",
                f"{scores['stability']:.1f}",
            ])

    print(f"Results saved to {csv_file}")

if __name__ == '__main__':
    score_all_tests()
