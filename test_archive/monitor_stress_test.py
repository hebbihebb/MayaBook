#!/usr/bin/env python3
"""
Monitor the ongoing stress test conversion

Provides real-time statistics on progress, speed, and estimated completion time.
"""
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

def monitor_stress_test(log_file_pattern="stress_test_*.log"):
    """Monitor the stress test progress"""

    # Find the most recent stress test log
    log_files = list(Path(".").glob(log_file_pattern))
    if not log_files:
        print("No stress test log found")
        return

    log_file = max(log_files, key=os.path.getctime)
    print(f"Monitoring: {log_file}")
    print("="*80)

    while True:
        try:
            with open(log_file, 'r') as f:
                content = f.read()

            # Find all progress lines
            progress_pattern = r'Progress: (\d+)/(\d+) chunks \(([0-9.]+)%\)'
            matches = re.findall(progress_pattern, content)

            if not matches:
                print("No progress found yet...")
                time.sleep(10)
                continue

            # Get the last progress update
            completed, total, percent = matches[-1]
            completed = int(completed)
            total = int(total)
            percent = float(percent)

            # Extract timestamps from log
            timestamp_pattern = r'2025-11-16 (\d{2}:\d{2}:\d{2})'
            timestamps = re.findall(timestamp_pattern, content)

            if not timestamps:
                print("No timestamps found...")
                time.sleep(10)
                continue

            # Calculate rate
            start_time_str = timestamps[0]
            current_time_str = timestamps[-1]

            try:
                start_dt = datetime.strptime(start_time_str, "%H:%M:%S")
                current_dt = datetime.strptime(current_time_str, "%H:%M:%S")
                elapsed = (current_dt - start_dt).total_seconds()

                if elapsed < 1:
                    elapsed = 1

                rate = completed / elapsed  # chunks per second
                chunks_remaining = total - completed

                if rate > 0:
                    seconds_remaining = chunks_remaining / rate
                    time_remaining = timedelta(seconds=seconds_remaining)
                    eta = datetime.now() + time_remaining
                else:
                    time_remaining = None
                    eta = None
            except:
                rate = 0
                time_remaining = None
                eta = None

            # Clear screen and print stats
            os.system('clear')
            print("="*80)
            print("STRESS TEST MONITOR")
            print("="*80)
            print(f"Log file: {log_file}")
            print(f"Last update: {current_time_str}")
            print()
            print(f"Progress:       {completed}/{total} chunks ({percent:.1f}%)")
            print(f"Speed:          {rate:.3f} chunks/second (~{rate*60:.1f} chunks/minute)")
            if time_remaining:
                hours = time_remaining.total_seconds() / 3600
                print(f"ETA:            {time_remaining} ({hours:.1f} hours)")
                print(f"Completion:     {eta.strftime('%H:%M:%S')}")
            print(f"Elapsed:        {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
            print("="*80)

            # Check for errors
            if "ERROR" in content:
                error_pattern = r'ERROR.*?$'
                errors = re.findall(error_pattern, content, re.MULTILINE)
                if errors:
                    print("\n⚠️  ERRORS DETECTED:")
                    for error in errors[-3:]:  # Show last 3 errors
                        print(f"  - {error[:70]}...")

            # Check for warnings
            if "WARNING" in content:
                warning_pattern = r'WARNING.*?$'
                warnings = re.findall(warning_pattern, content, re.MULTILINE)
                if warnings:
                    print(f"\n⚠️  Warnings: {len(warnings)}")
                    for warning in warnings[-2:]:  # Show last 2 warnings
                        print(f"  - {warning[:70]}...")

            print("\nPress Ctrl+C to exit")
            time.sleep(30)  # Update every 30 seconds

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_stress_test()
