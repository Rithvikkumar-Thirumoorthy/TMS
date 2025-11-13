#!/usr/bin/env python3
"""
Quick runner for NDC optimization
Simply run: python run_ndc.py
"""
from run_tms_optimization import run_single_day_optimization, run_weekly_optimization
import sys

def main():
    print("\n" + "="*70)
    print("🚛 NDC DISTRIBUTION CENTER - VRP OPTIMIZATION")
    print("="*70)

    print("\nWhat would you like to optimize?")
    print("1. Single Day (Monday)")
    print("2. Single Day (choose day)")
    print("3. Full Week (Mon-Fri)")
    print("4. Compare Algorithms")

    choice = input("\nEnter choice (1-4) [1]: ").strip() or "1"

    if choice == "1":
        print("\n🚀 Optimizing NDC Monday with OR-Tools...")
        run_single_day_optimization(target_dc="NDC", day="Mon", algorithm="ortools", time_limit=60)

    elif choice == "2":
        day = input("Enter day (Mon/Tue/Wed/Thu/Fri) [Mon]: ").strip() or "Mon"
        print(f"\n🚀 Optimizing NDC {day} with OR-Tools...")
        run_single_day_optimization(target_dc="NDC", day=day, algorithm="ortools", time_limit=60)

    elif choice == "3":
        print("\n🚀 Optimizing NDC Full Week (Mon-Fri)...")
        run_weekly_optimization(target_dc="NDC", algorithm="clarke-wright")

    elif choice == "4":
        day = input("Enter day (Mon/Tue/Wed/Thu/Fri) [Mon]: ").strip() or "Mon"
        print(f"\n🚀 Comparing algorithms for NDC {day}...")

        print("\n" + "="*70)
        print("1. CLARKE-WRIGHT (Fast baseline)")
        print("="*70)
        run_single_day_optimization(target_dc="NDC", day=day, algorithm="clarke-wright", time_limit=30)

        print("\n" + "="*70)
        print("2. OR-TOOLS (Production quality)")
        print("="*70)
        run_single_day_optimization(target_dc="NDC", day=day, algorithm="ortools", time_limit=60)

    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
