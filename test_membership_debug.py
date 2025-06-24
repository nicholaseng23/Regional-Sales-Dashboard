#!/usr/bin/env python3
"""
Debug script to test Membership data fetching
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from google_sheets_client import GoogleSheetsClient
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_membership_data():
    """Test the membership data fetching for each country."""
    
    client = GoogleSheetsClient()
    
    # Test each country's membership data
    countries = ['membership_dashboard_my', 'membership_dashboard_ph', 'membership_dashboard_th']
    
    for country in countries:
        print(f"\n{'='*50}")
        print(f"Testing {country}")
        print(f"{'='*50}")
        
        try:
            # Get the data
            data = client.get_sheet_data(country)
            print(f"Raw data: {data}")
            
            if data.get('raw_data'):
                print(f"Raw data keys: {list(data['raw_data'].keys())}")
                print(f"Raw data values: {data['raw_data']}")
            
            if data.get('monthly_data'):
                print(f"Monthly data keys: {list(data['monthly_data'].keys())}")
                for month, month_data in data['monthly_data'].items():
                    print(f"  {month}: {month_data}")
            
        except Exception as e:
            print(f"Error testing {country}: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_membership_data() 