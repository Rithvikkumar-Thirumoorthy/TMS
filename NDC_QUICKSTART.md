# NDC Distribution Center - Quick Start Guide

The system is now configured for **NDC (Northern Distribution Center)** optimization.

## 📊 Your Data Summary

- **Distribution Center:** NDC at (5.3149, 100.4492)
- **Total Stores:** 230
- **Fleet Size:** 32 vehicles
- **Pre-calculated Matrices:** ✅ Distance & Time matrices loaded

### Monday Sample Results (Clarke-Wright):
- **Stores with orders:** 156
- **Total demand:** 525.30 CBM
- **Vehicles used:** 31/32
- **Total distance:** 1,993.54 km
- **Average utilization:** 76.8%
- **Optimized routes:** Multi-stop consolidated routes

---

## 🚀 Quick Commands

### 1. Run NDC Optimization (Interactive)
```bash
python run_ndc.py
```

Choose from menu:
1. Single Day (Monday) - Quick test
2. Single Day (choose day) - Optimize any weekday
3. Full Week (Mon-Fri) - Complete weekly optimization
4. Compare Algorithms - See different solver results

### 2. Run Specific Day (Command Line)
```python
# Monday with OR-Tools
python -c "from run_tms_optimization import run_single_day_optimization; run_single_day_optimization('NDC', 'Mon', 'ortools')"

# Tuesday with Clarke-Wright (faster)
python -c "from run_tms_optimization import run_single_day_optimization; run_single_day_optimization('NDC', 'Tue', 'clarke-wright')"

# Wednesday with ALNS (best quality, slower)
python -c "from run_tms_optimization import run_single_day_optimization; run_single_day_optimization('NDC', 'Wed', 'alns')"
```

### 3. Run Full Week Optimization
```python
python -c "from run_tms_optimization import run_weekly_optimization; run_weekly_optimization('NDC', 'ortools')"
```

---

## 📁 Output Files

Results are saved to `output/` directory:

**Single Day:**
- `solution_NDC_Mon_ortools.json` - Complete solution data
- `solution_NDC_Mon_ortools.csv` - Route details in CSV

**Weekly:**
- `weekly_summary_NDC_ortools.json` - Full week summary

---

## 🎯 Algorithm Comparison

| Algorithm | Speed | Quality | Best For |
|-----------|-------|---------|----------|
| **Clarke-Wright** | ⚡⚡⚡ Fast (< 30 sec) | Good (85-90% optimal) | Quick prototyping |
| **OR-Tools** | ⚡⚡ Medium (1-2 min) | Excellent (95-98% optimal) | Production use |
| **ALNS** | ⚡ Slow (5-10 min) | Best (98-99% optimal) | High-quality solutions |

**Recommended:** Use **OR-Tools** for production - best balance of speed and quality.

---

## 📊 What Gets Optimized

### Hard Constraints (Must satisfy):
✅ Vehicle capacity (22-30 CBM per truck)
✅ Time windows (store opening hours)
✅ Service time (60 min per store)
✅ Max route duration (12 hours)
✅ Day exclusions (closed days)

### Optimization Goals:
🎯 Minimize total distance
🎯 Minimize vehicles used
🎯 Maximize capacity utilization (target: 85%)
🎯 Balance load across fleet

---

## 🔍 Checking Results

After optimization, you'll see:

```
📊 OPTIMIZATION RESULTS
✓ Feasible: True
✓ Vehicles used: 31/32
✓ Stores served: 156/156
✓ Total distance: 1993.54 km
✓ Average utilization: 76.8%

📦 ROUTES SUMMARY
Route 1 - VCH8730
  Stops: 5 stores
  Sequence: DA03 → Q119 → Q023 → P172 → Q052
  Distance: 86.28 km
  Load: 16.39/22.06 CBM (74.3%)
```

---

## 🛠️ Other Distribution Centers

The system supports 4 DCs:
1. **NDC** (default) - 230 stores
2. **EDC** - Eastern DC
3. **DC_KLANG** - Klang DC
4. **HQ** - Headquarters DC

To optimize for a different DC:
```python
run_single_day_optimization(target_dc='EDC', day='Mon', algorithm='ortools')
```

---

## 📞 Need Help?

- Check `README.md` for full documentation
- See `examples/` for code samples
- Review `Input/README.md` for data format

---

**System ready for NDC optimization! 🚛📦**
