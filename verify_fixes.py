#!/usr/bin/env python3
"""
Comprehensive verification checklist for FLEditor v4.1 bug fixes.
This script verifies all critical components without launching the GUI.
"""

import importlib.util
from pathlib import Path

def check_method_exists(obj, method_name):
    """Check if object has a callable method."""
    return hasattr(obj, method_name) and callable(getattr(obj, method_name))

def main():
    # Load module
    spec = importlib.util.spec_from_file_location("fleditor", 
                                                    "/home/steven/FLEditor/Fleditor-V4.1.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    print("=" * 70)
    print("FLEditor v4.1 - Bug Fixes Verification Checklist")
    print("=" * 70)
    
    results = {
        "PASSED": [],
        "FAILED": []
    }
    
    # Test 1: ZoneItem class
    print("\n[1] ZoneItem Class")
    try:
        zone_data = {
            "_entries": [
                ("nickname", "test_zone"),
                ("pos", "0, 0, 0"),
            ]
        }
        zone = module.ZoneItem(zone_data, 1.0)
        
        # Check for raw_text method
        if check_method_exists(zone, 'raw_text'):
            raw_text_output = zone.raw_text()
            if "nickname = test_zone" in raw_text_output:
                print("  ✓ ZoneItem.raw_text() works correctly")
                results["PASSED"].append("ZoneItem.raw_text()")
            else:
                print("  ✗ ZoneItem.raw_text() output unexpected")
                results["FAILED"].append("ZoneItem.raw_text() output")
        else:
            print("  ✗ ZoneItem missing raw_text() method")
            results["FAILED"].append("ZoneItem.raw_text() method")
    except Exception as e:
        print(f"  ✗ Error testing ZoneItem: {e}")
        results["FAILED"].append(f"ZoneItem: {e}")
    
    # Test 2: SolarObject class
    print("\n[2] SolarObject Class")
    try:
        obj_data = {
            "_entries": [
                ("nickname", "test_object"),
                ("pos", "0, 0, 0"),
            ],
            "archetype": "STAR"
        }
        obj = module.SolarObject(obj_data, 1.0, None)
        
        if check_method_exists(obj, 'raw_text'):
            print("  ✓ SolarObject has raw_text() method")
            results["PASSED"].append("SolarObject.raw_text()")
        else:
            print("  ✗ SolarObject missing raw_text() method")
            results["FAILED"].append("SolarObject.raw_text()")
            
        if check_method_exists(obj, 'apply_text'):
            print("  ✓ SolarObject has apply_text() method")
            results["PASSED"].append("SolarObject.apply_text()")
        else:
            print("  ✗ SolarObject missing apply_text() method")
            results["FAILED"].append("SolarObject.apply_text()")
    except Exception as e:
        print(f"  ✗ Error testing SolarObject: {e}")
        results["FAILED"].append(f"SolarObject: {e}")
    
    # Test 3: SystemView signals
    print("\n[3] SystemView Signals")
    try:
        view = module.SystemView()
        signals = ['object_selected', 'background_clicked', 'zone_clicked', 'system_double_clicked']
        
        for sig in signals:
            if hasattr(view, sig):
                print(f"  ✓ SystemView.{sig} exists")
                results["PASSED"].append(f"Signal: {sig}")
            else:
                print(f"  ✗ SystemView.{sig} missing")
                results["FAILED"].append(f"Signal: {sig}")
    except Exception as e:
        print(f"  ✗ Error testing SystemView: {e}")
        results["FAILED"].append(f"SystemView: {e}")
    
    # Test 4: MainWindow methods (without instantiating)
    print("\n[4] MainWindow Methods")
    try:
        methods = [
            '_delete_object',
            '_delete_counterpart', 
            '_select_zone',
            '_start_zone_creation',
            '_create_zone_at_pos',
            '_on_background_click',
            '_write_to_file',
        ]
        
        for method in methods:
            if hasattr(module.MainWindow, method):
                print(f"  ✓ MainWindow.{method}() defined")
                results["PASSED"].append(f"Method: {method}")
            else:
                print(f"  ✗ MainWindow.{method}() missing")
                results["FAILED"].append(f"Method: {method}")
    except Exception as e:
        print(f"  ✗ Error checking MainWindow: {e}")
        results["FAILED"].append(f"MainWindow: {e}")
    
    # Test 5: Helper functions
    print("\n[5] Helper Functions")
    try:
        helpers = ['_ci_find', 'ci_resolve', 'FLParser']
        for helper in helpers:
            if hasattr(module, helper):
                print(f"  ✓ {helper} function exists")
                results["PASSED"].append(f"Helper: {helper}")
            else:
                print(f"  ✗ {helper} function missing")
                results["FAILED"].append(f"Helper: {helper}")
    except Exception as e:
        print(f"  ✗ Error checking helpers: {e}")
        results["FAILED"].append(f"Helpers: {e}")
    
    # Test 6: Dialog class
    print("\n[6] ZoneCreationDialog")
    try:
        # Check if dialog exists
        if hasattr(module, 'ZoneCreationDialog'):
            print("  ✓ ZoneCreationDialog class exists")
            results["PASSED"].append("Dialog: ZoneCreationDialog")
        else:
            print("  ✗ ZoneCreationDialog class missing")
            results["FAILED"].append("Dialog: ZoneCreationDialog")
    except Exception as e:
        print(f"  ✗ Error checking dialog: {e}")
        results["FAILED"].append(f"Dialog: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = len(results["PASSED"])
    failed = len(results["FAILED"])
    total = passed + failed
    
    print(f"\nTests Passed: {passed}/{total}")
    print(f"Tests Failed: {failed}/{total}")
    
    if results["PASSED"]:
        print("\n✓ PASSED CHECKS:")
        for check in results["PASSED"]:
            print(f"  • {check}")
    
    if results["FAILED"]:
        print("\n✗ FAILED CHECKS:")
        for check in results["FAILED"]:
            print(f"  • {check}")
    
    print("\n" + "=" * 70)
    if failed == 0:
        print("✓ ALL CHECKS PASSED - Module is ready for testing!")
    else:
        print(f"⚠ {failed} issues remaining")
    print("=" * 70)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
