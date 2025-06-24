#!/usr/bin/env python3
"""
Debug script to test Sales Funnel data fetching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_sheets_client import GoogleSheetsClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_sales_funnel_data():
    """Test the sales funnel data fetching for each country."""
    
    client = GoogleSheetsClient()
    
    # Test each country's sales funnel data
    countries = ['sales_funnel_my', 'sales_funnel_ph', 'sales_funnel_th']
    
    for country in countries:
        print(f"\n{'='*50}")
        print(f"Testing {country}")
        print(f"{'='*50}")
        
        try:
            # Get the worksheet
            from config import GOOGLE_SHEETS_CONFIG
            sheet_config = GOOGLE_SHEETS_CONFIG['sheets'][country]
            sheet_id = sheet_config['id']
            worksheet_name = sheet_config['worksheet_name']
            
            print(f"Sheet ID: {sheet_id}")
            print(f"Worksheet: {worksheet_name}")
            
            # Open the sheet
            sheet = client.client.open_by_key(sheet_id)
            worksheet = sheet.worksheet(worksheet_name)
            
            print(f"Successfully opened worksheet: {worksheet.title}")
            
            # Test the data fetching
            result = client.get_sales_funnel_data(worksheet, country)
            
            print(f"Raw data keys: {list(result.keys())}")
            
            if 'table_data' in result:
                table_data = result['table_data']
                print(f"Number of data points: {len(table_data)}")
                
                if table_data:
                    print("\nFirst data point:")
                    for key, value in table_data[0].items():
                        print(f"  {key}: {value}")
                    
                    print("\nAll data points:")
                    for i, data_point in enumerate(table_data):
                        print(f"  Point {i+1}: {data_point}")
                else:
                    print("No table data found")
            
            if 'raw_data' in result:
                raw_data = result['raw_data']
                print(f"\nRaw data: {raw_data}")
                
        except Exception as e:
            print(f"Error testing {country}: {e}")
            logger.error(f"Error testing {country}: {e}", exc_info=True)

if __name__ == "__main__":
    test_sales_funnel_data() 