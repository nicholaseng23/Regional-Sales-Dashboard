#!/usr/bin/env python3
"""
Simple test script to debug Sales Funnel data fetching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_sheets_client import GoogleSheetsClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_funnel():
    """Simple test of sales funnel data fetching."""
    
    client = GoogleSheetsClient()
    
    try:
        # Test with Malaysia first
        from config import GOOGLE_SHEETS_CONFIG
        sheet_config = GOOGLE_SHEETS_CONFIG['sheets']['sales_funnel_my']
        sheet_id = sheet_config['id']
        worksheet_name = sheet_config['worksheet_name']
        
        print(f"Sheet ID: {sheet_id}")
        print(f"Worksheet: {worksheet_name}")
        
        # Open the sheet
        sheet = client.client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)
        
        print(f"Successfully opened worksheet: {worksheet.title}")
        
        # Test a simple range first
        print("\nTesting simple range BE54:BS63...")
        try:
            simple_data = worksheet.batch_get(['BE54:BS63'])
            print(f"Type of result: {type(simple_data)}")
            print(f"Length of result: {len(simple_data) if simple_data else 0}")
            if simple_data:
                print(f"First element type: {type(simple_data[0])}")
                print(f"First element: {simple_data[0]}")
                if simple_data[0]:
                    print(f"Number of rows: {len(simple_data[0])}")
                    print(f"First row: {simple_data[0][0] if simple_data[0] else 'None'}")
        except Exception as e:
            print(f"Error with simple range: {e}")
        
        # Test getting all values
        print("\nTesting get_all_values()...")
        try:
            all_values = worksheet.get_all_values()
            print(f"All values type: {type(all_values)}")
            print(f"Number of rows: {len(all_values)}")
            if all_values:
                print(f"First row: {all_values[0]}")
                print(f"Last row: {all_values[-1]}")
        except Exception as e:
            print(f"Error with get_all_values: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    test_simple_funnel() 