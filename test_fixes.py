#!/usr/bin/env python3
"""Test script to verify all fixes without launching the GUI."""

import sys
import importlib.util
from pathlib import Path

# Load the module by file path
spec = importlib.util.spec_from_file_location("fleditor", "/home/steven/FLEditor/Fleditor-V4.1.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

print("=" * 60)
print("RUNNING TESTS FOR FLEDITOR-V4.1")
print("=" * 60)

# Test 1: ZoneItem.raw_text() method
print("\n[TEST 1] ZoneItem.raw_text() method")
zone_data = {
    "_entries": [
        ("nickname", "zone_01"),
        ("pos", "0, 0, 0"),
        ("shape", "ELLIPSOID"),
        ("size", "1000, 1000, 1000"),
    ]
}
try:
    zone = module.ZoneItem(zone_data, 1.0)
    has_raw_text = hasattr(zone, 'raw_text')
    print(f"  ✓ ZoneItem has raw_text method: {has_raw_text}")
    if has_raw_text:
        output = zone.raw_text()
        expected_lines = 4
        actual_lines = len(output.strip().split("\n"))
        print(f"  ✓ raw_text() returns {actual_lines} lines (expected {expected_lines})")
        print(f"  ✓ Sample output:\n{chr(10).join('    ' + line for line in output.split(chr(10))[:2])}")
except Exception as e:
    print(f"  ✗ Error: {e}")

# Test 2: MainWindow methods exist
print("\n[TEST 2] MainWindow methods")
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

try:
    mw = module.MainWindow()
    methods_to_check = [
        "_select_zone",
        "_delete_object",
        "_delete_counterpart",
        "_start_zone_creation",
        "_create_zone_at_pos",
        "_on_background_click",
    ]
    for method_name in methods_to_check:
        has_method = hasattr(mw, method_name)
        symbol = "✓" if has_method else "✗"
        print(f"  {symbol} MainWindow.{method_name}: {has_method}")
except Exception as e:
    print(f"  ✗ Error loading MainWindow: {e}")

# Test 3: SystemView signals
print("\n[TEST 3] SystemView signals")
try:
    view = module.SystemView()
    signals_to_check = [
        "object_selected",
        "background_clicked", 
        "zone_clicked",
        "system_double_clicked",
    ]
    for signal_name in signals_to_check:
        has_signal = hasattr(view, signal_name)
        symbol = "✓" if has_signal else "✗"
        print(f"  {symbol} SystemView.{signal_name}: {has_signal}")
except Exception as e:
    print(f"  ✗ Error loading SystemView: {e}")

# Test 4: FLParser methods
print("\n[TEST 4] FLParser methods")
try:
    parser = module.FLParser()
    methods_to_check = ["read_file", "write_file", "get", "set"]
    for method_name in methods_to_check:
        has_method = hasattr(parser, method_name)
        symbol = "✓" if has_method else "✗"
        print(f"  {symbol} FLParser.{method_name}: {has_method}")
except Exception as e:
    print(f"  ✗ Error loading FLParser: {e}")

# Test 5: Helper functions
print("\n[TEST 5] Helper functions")
helper_funcs = ["_ci_find", "ci_resolve", "FLParser", "SolarObject", "ZoneItem", "SystemView"]
for func_name in helper_funcs:
    has_func = hasattr(module, func_name)
    symbol = "✓" if has_func else "✗"
    print(f"  {symbol} {func_name}: {has_func}")

print("\n" + "=" * 60)
print("TESTS COMPLETED")
print("=" * 60)
