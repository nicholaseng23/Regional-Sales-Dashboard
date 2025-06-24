#!/usr/bin/env python3
"""
Test script to check sales funnel data fetching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_sheets_client import GoogleSheetsClient
from config import GOOGLE_SHEETS_CONFIG
import json

def test_sales_funnel_data():
    """Test sales funnel data fetching for all countries"""
    
    print("🔍 Testing Sales Funnel Data Fetching...")
    print("=" * 50)
    
    client = GoogleSheetsClient()
    
    # Test each sales funnel sheet
    funnel_sheets = ['sales_funnel_my', 'sales_funnel_ph', 'sales_funnel_th']
    
    for sheet_key in funnel_sheets:
        print(f"\n📊 Testing {sheet_key}...")
        
        try:
            # Get sheet data
            sheet_data = client.get_sheet_data(sheet_key)
            
            if sheet_data:
                print(f"✅ Successfully fetched data for {sheet_key}")
                
                # Check if we have table data
                table_data = sheet_data.get('table_data', [])
                raw_data = sheet_data.get('raw_data', {})
                
                print(f"   📋 Table data rows: {len(table_data)}")
                print(f"   📊 Raw data keys: {list(raw_data.keys()) if raw_data else 'None'}")
                
                # Show first few rows of table data
                if table_data:
                    print(f"   📈 Sample data (first 2 rows):")
                    for i, row in enumerate(table_data[:2]):
                        print(f"      Row {i+1}: {row}")
                else:
                    print("   ⚠️  No table data found")
                
                # Show raw data
                if raw_data:
                    print(f"   📊 Raw data: {raw_data}")
                else:
                    print("   ⚠️  No raw data found")
                    
            else:
                print(f"❌ Failed to fetch data for {sheet_key}")
                
        except Exception as e:
            print(f"❌ Error testing {sheet_key}: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Testing complete!")

if __name__ == "__main__":
    test_sales_funnel_data() 