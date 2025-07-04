import gspread
import json
import os
import re
import time
import logging
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta

# Handle streamlit import gracefully for cloud deployment
try:
    import streamlit as st
except ImportError:
    st = None

# Handle config import gracefully
try:
    from config import GOOGLE_SHEETS_CONFIG
except ImportError:
    # Fallback configuration for cloud deployment
    GOOGLE_SHEETS_CONFIG = {
        'sheets': {}
    }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DURATION = 14400  # 4 hours cache (reduced from 8 hours)
REQUEST_DELAY = 5.0  # 5 seconds between requests (reduced from 15 seconds)
MAX_RETRIES = 2  # Reduced to fail faster

class GoogleSheetsClient:
    def __init__(self):
        self.client = None
        self.api_call_count = 0
        self.last_api_call_time = 0
        self.REQUEST_DELAY = REQUEST_DELAY  # Store as instance variable
        self.last_error_type = None  # Track the type of last error
        self.last_error_message = None  # Track the last error message
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the Google Sheets client with proper credential handling for cloud deployment"""
        try:
            # Check for environment variable first (for cloud deployment)
            credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
            
            if credentials_json:
                # Cloud deployment: credentials from environment variable
                logger.info("Using credentials from environment variable")
                credentials_dict = json.loads(credentials_json)
                credentials = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets.readonly",
                        "https://www.googleapis.com/auth/drive.readonly"
                    ]
                )
            else:
                # Local development: credentials from file
                logger.info("Using credentials from local file")
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError("credentials.json not found. Please add your Google Sheets API credentials.")
                
                credentials = Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=[
                        "https://www.googleapis.com/auth/spreadsheets.readonly",
                        "https://www.googleapis.com/auth/drive.readonly"
                    ]
                )
            
            self.client = gspread.authorize(credentials)
            logger.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            self.client = None
            raise
    
    def _rate_limit_delay(self):
        """Implement rate limiting to prevent API quota exhaustion."""
        current_time = time.time()
        time_since_last = current_time - self.last_api_call_time
        
        # Ensure minimum delay between requests
        if time_since_last < self.REQUEST_DELAY:
            sleep_time = self.REQUEST_DELAY - time_since_last
            logger.info(f"⏳ Rate limiting: waiting {sleep_time:.1f} seconds")
            time.sleep(sleep_time)
        
        self.last_api_call_time = time.time()
    
    def exponential_backoff(self, attempt):
        """Implement exponential backoff for rate limiting"""
        delay = min(3 ** attempt, 180)  # Max 180 seconds (increased from 120)
        time.sleep(delay)
        logger.warning(f"🔄 Rate limited, waiting {delay} seconds (attempt {attempt + 1})")
    
    def batch_get_all_sheet_data(self, sheet_id, worksheet_name, ranges_dict):
        """
        Optimized batch data fetching using Google Sheets API batchGet.
        
        Args:
            sheet_id: Google Sheets ID
            worksheet_name: Name of the worksheet
            ranges_dict: Dictionary mapping data types to their ranges
                        e.g., {'vip_data': ['A1:Z1', 'A2:Z2'], 'funnel_data': ['BE54:BS63']}
        
        Returns:
            Dictionary with the same keys as ranges_dict, containing the fetched data
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Get worksheet (this already applies rate limiting)
                worksheet = self._get_worksheet(sheet_id, worksheet_name)
                if not worksheet:
                    logger.error(f"Could not access worksheet {worksheet_name} in sheet {sheet_id}")
                    return {}
                
                # Flatten all ranges into a single list for batch request
                all_ranges = []
                range_mapping = {}  # Maps range index to (data_type, range_index)
                
                for data_type, ranges in ranges_dict.items():
                    for i, range_str in enumerate(ranges):
                        range_mapping[len(all_ranges)] = (data_type, i)
                        all_ranges.append(range_str)
                
                if not all_ranges:
                    return {}
                
                logger.info(f"Batch fetching {len(all_ranges)} ranges from {worksheet_name}")
                
                # Single batch API call for all ranges
                batch_data = worksheet.batch_get(all_ranges)
                self.api_call_count += 1
                
                # Organize results back into the original structure
                result = {data_type: [] for data_type in ranges_dict.keys()}
                
                for range_idx, data in enumerate(batch_data):
                    if range_idx in range_mapping:
                        data_type, original_range_idx = range_mapping[range_idx]
                        # Ensure we have enough slots in the result list
                        while len(result[data_type]) <= original_range_idx:
                            result[data_type].append([])
                        result[data_type][original_range_idx] = data
                
                logger.info(f"✅ Successfully batch fetched data from {worksheet_name} (API calls: {self.api_call_count})")
                return result
                
            except gspread.exceptions.APIError as e:
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    self._record_error('RATE_LIMIT', str(e))
                    logger.warning(f"⚠️ API rate limit exceeded for {worksheet_name}")
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                    else:
                        logger.error(f"❌ Max retries exceeded for {worksheet_name} due to rate limiting")
                else:
                    self._record_error('API_ERROR', str(e))
                logger.error(f"❌ API Error in batch_get_all_sheet_data: {e}")
                return {}
            except Exception as e:
                self._record_error('GENERAL_ERROR', str(e))
                logger.error(f"❌ Error in batch_get_all_sheet_data: {e}")
                return {}
        
        return {}
    
    def find_month_columns_batch(self, header_row):
        """
        Find all month columns from header row in a single operation.
        Returns dictionary mapping month names to column letters.
        """
        month_columns = {}
        date_pattern = r'(\d{2})-(\d{2})'  # Pattern for 'YY-MM'
        
        for i, cell_value in enumerate(header_row):
            match = re.search(date_pattern, str(cell_value))
            if match:
                year, month = match.groups()
                month_name = datetime(int(f"20{year}"), int(month), 1).strftime("%B %Y")
                column_letter = self._index_to_column_letter(i)
                month_columns[month_name] = column_letter
        
        return month_columns
    
    def _index_to_column_letter(self, col_idx):
        """Convert column index to Excel column letter (0-based index)"""
        result = ""
        while col_idx >= 0:
            result = chr(col_idx % 26 + ord('A')) + result
            col_idx = col_idx // 26 - 1
        return result
    
    def process_vip_data_batch(self, worksheet):
        """
        Optimized VIP data processing using batch operations.
        Fetches header row and all month data in a single API call.
        """
        try:
            # Get all possible month columns (assume up to 24 months of data)
            # This covers a wide range to ensure we get all data in one call
            month_ranges = []
            for col_idx in range(22, 46):  # Columns V to AT (covers 24 months)
                col_letter = self._index_to_column_letter(col_idx)
                month_ranges.extend([
                    f"{col_letter}1",   # header
                    f"{col_letter}2",   # total_deals
                    f"{col_letter}28",  # onsite_vip
                    f"{col_letter}30"   # remote_vip
                ])
            
            # Single batch request for header and all data
            ranges_dict = {'all_data': month_ranges}
            batch_result = self.batch_get_all_sheet_data(
                worksheet.spreadsheet.id, 
                worksheet.title, 
                ranges_dict
            )
            
            if not batch_result or 'all_data' not in batch_result:
                logger.warning(f"Could not fetch data from {worksheet.title}")
                return {'raw_data': {}, 'monthly_data': {}}
            
            # Process batch results
            all_data = batch_result['all_data']
            monthly_data = {}
            date_pattern = r'(\d{2})-(\d{2})'  # Pattern for 'YY-MM'
            
            # Process in groups of 4 (header, total_deals, onsite_vip, remote_vip)
            for i in range(0, len(all_data), 4):
                if i + 3 < len(all_data):
                    try:
                        # Extract header value
                        header_cell = all_data[i]
                        header_value = header_cell[0][0] if header_cell and len(header_cell) > 0 and len(header_cell[0]) > 0 else ""
                        
                        # Check if this is a valid month header
                        match = re.search(date_pattern, str(header_value))
                        if match:
                            year, month = match.groups()
                            month_name = datetime(int(f"20{year}"), int(month), 1).strftime("%B %Y")
                            col_letter = self._index_to_column_letter(22 + (i // 4))
                            
                            # Extract data values
                            total_deals = self._extract_cell_value([all_data[i + 1]])
                            onsite_vip = self._extract_cell_value([all_data[i + 2]])
                            remote_vip = self._extract_cell_value([all_data[i + 3]])
                            
                            if total_deals > 0:  # Only include months with data
                                monthly_data[month_name] = {
                                    'total_deals': total_deals,
                                    'onsite_vip_deals': onsite_vip,
                                    'remote_vip_deals': remote_vip,
                                    'month_label': f"{datetime.strptime(month_name, '%B %Y').strftime('%B')} ({col_letter})"
                                }
                    except Exception as e:
                        logger.warning(f"Error processing month data at index {i}: {e}")
                        continue
            
            # Sort months and get latest
            sorted_months = dict(sorted(monthly_data.items(), 
                                      key=lambda item: datetime.strptime(item[0], '%B %Y'), 
                                      reverse=True))
            latest_month_data = list(sorted_months.values())[0] if sorted_months else {}
            
            logger.info(f"Processed VIP data for {len(sorted_months)} months in single API call")
            return {
                'raw_data': latest_month_data,
                'monthly_data': sorted_months
            }
            
        except Exception as e:
            logger.error(f"Error in process_vip_data_batch: {e}")
            return {'raw_data': {}, 'monthly_data': {}}
    
    def process_membership_data_batch(self, worksheet):
        """
        Optimized membership data processing using batch operations.
        Fetches header row and all month data in a single API call.
        """
        try:
            # Get all possible month columns (assume up to 24 months of data)
            # This covers a wide range to ensure we get all data in one call
            month_ranges = []
            for col_idx in range(22, 46):  # Columns V to AT (covers 24 months)
                col_letter = self._index_to_column_letter(col_idx)
                month_ranges.extend([
                    f"{col_letter}1",   # header
                    f"{col_letter}2",   # total_deals
                ])
                
                # For Thailand, we need different rows
                if worksheet.title == 'TH':
                    month_ranges.extend([f"{col_letter}30", f"{col_letter}31"])
                else:
                    month_ranges.extend([f"{col_letter}43", f"{col_letter}44"])
            
            # Single batch request for header and all data
            ranges_dict = {'all_data': month_ranges}
            batch_result = self.batch_get_all_sheet_data(
                worksheet.spreadsheet.id, 
                worksheet.title, 
                ranges_dict
            )
            
            if not batch_result or 'all_data' not in batch_result:
                logger.warning(f"Could not fetch data from {worksheet.title}")
                return {'raw_data': {}, 'monthly_data': {}}
            
            # Process batch results
            all_data = batch_result['all_data']
            monthly_data = {}
            date_pattern = r'(\d{2})-(\d{2})'  # Pattern for 'YY-MM'
            
            # Process in groups of 4 (header, total_deals, membership_1, membership_2)
            for i in range(0, len(all_data), 4):
                if i + 3 < len(all_data):
                    try:
                        # Extract header value
                        header_cell = all_data[i]
                        header_value = header_cell[0][0] if header_cell and len(header_cell) > 0 and len(header_cell[0]) > 0 else ""
                        
                        # Check if this is a valid month header
                        match = re.search(date_pattern, str(header_value))
                        if match:
                            year, month = match.groups()
                            month_name = datetime(int(f"20{year}"), int(month), 1).strftime("%B %Y")
                            col_letter = self._index_to_column_letter(22 + (i // 4))
                            
                            # Extract data values
                            total_deals = self._extract_cell_value([all_data[i + 1]])
                            membership_1 = self._extract_cell_value([all_data[i + 2]])
                            membership_2 = self._extract_cell_value([all_data[i + 3]])
                            
                            if total_deals > 0:  # Only include months with data
                                monthly_data[month_name] = {
                                    'total_deals': total_deals,
                                    'membership_1': membership_1,
                                    'membership_2': membership_2,
                                    'month_label': f"{datetime.strptime(month_name, '%B %Y').strftime('%B')} ({col_letter})"
                                }
                    except Exception as e:
                        logger.warning(f"Error processing month data at index {i}: {e}")
                        continue
            
            # Sort months and get latest
            sorted_months = dict(sorted(monthly_data.items(), 
                                      key=lambda item: datetime.strptime(item[0], '%B %Y'), 
                                      reverse=True))
            latest_month_data = list(sorted_months.values())[0] if sorted_months else {}
            
            logger.info(f"Processed membership data for {len(sorted_months)} months in single API call")
            return {
                'raw_data': latest_month_data,
                'monthly_data': sorted_months
            }
            
        except Exception as e:
            logger.error(f"Error in process_membership_data_batch: {e}")
            return {'raw_data': {}, 'monthly_data': {}}
    
    def process_funnel_data_batch(self, worksheet, sheet_key):
        """
        Optimized funnel data processing using batch operations.
        Fetches all funnel ranges in a single API call.
        """
        try:
            # Define the ranges for each country
            ranges_config = {
                'sales_funnel_my': ['BE54:BS63', 'BE74:BS83', 'BE94:BS103'],
                'sales_funnel_ph': ['BD53:BT84'],
                'sales_funnel_th': ['BH47:BV78'],
            }
            
            ranges = ranges_config.get(sheet_key, [])
            if not ranges:
                logger.error(f"No range configuration found for {sheet_key}")
                return {'raw_data': {}, 'table_data': []}
            
            # Single batch request for all funnel ranges
            ranges_dict = {'funnel_data': ranges}
            batch_result = self.batch_get_all_sheet_data(
                worksheet.spreadsheet.id, 
                worksheet.title, 
                ranges_dict
            )
            
            if not batch_result or 'funnel_data' not in batch_result:
                return {'raw_data': {}, 'table_data': []}
            
            # Process the batch results
            all_data = []
            for range_data in batch_result['funnel_data']:
                if range_data:
                    all_data.extend(range_data)
            
            if not all_data:
                logger.warning(f"No data found in ranges for {sheet_key}")
                return {'raw_data': {}, 'table_data': []}
            
            # Filter and process the data
            filtered_data = [row for row in all_data if len(row) >= 14]
            
            table_data = []
            for row in filtered_data:
                # Skip header rows
                first_col = str(row[0]).strip() if row[0] else ""
                if any(header_keyword in first_col.lower() 
                      for header_keyword in ['status', 'timestamp', 'update', 'header', 'title', 'created date']):
                    continue
                
                # Skip rows that don't look like dates
                if len(first_col) < 8 or not any(char.isdigit() for char in first_col):
                    continue
                
                table_row = {
                    'created_date': row[0],
                    'sum_of_won': row[6],
                    'lead_mql_pct': row[7],
                    'mql_sql_pct': row[8],
                    'sql_ms_pct': row[9],
                    'ms_mc_pct': row[10],
                    'lead_to_win_pct': row[13],
                    'lead_to_sql_pct': row[14],
                }
                table_data.append(table_row)
            
            # Use the most recent data point for raw_data
            latest_data = table_data[-1] if table_data else {}
            
            logger.info(f"Batch processed funnel data for {sheet_key}: {len(table_data)} data points")
            return {
                'raw_data': latest_data,
                'table_data': table_data
            }
            
        except Exception as e:
            logger.error(f"Error in process_funnel_data_batch: {e}")
            return {'raw_data': {}, 'table_data': []}
    
    def process_velocity_data_batch(self, worksheet):
        """
        Optimized velocity data processing using batch operations.
        Fetches all velocity data in a single API call.
        """
        try:
            # Use batch operation to get all data instead of get_all_values()
            # This ensures proper rate limiting
            ranges_dict = {'all_data': [f'A1:Z1000']}  # Get a large range to cover all data
            
            batch_result = self.batch_get_all_sheet_data(
                worksheet.spreadsheet.id, 
                worksheet.title, 
                ranges_dict
            )
            
            if not batch_result or 'all_data' not in batch_result:
                logger.warning("No data found in Sales Velocity worksheet")
                return {'raw_data': {}, 'weekly_data': []}
            
            # Extract all values from batch result
            all_values = batch_result['all_data'][0] if batch_result['all_data'] else []
            
            if not all_values:
                logger.warning("No data found in Sales Velocity worksheet")
                return {'raw_data': {}, 'weekly_data': []}
            
            logger.info(f"Sales Velocity sheet has {len(all_values)} rows")
            
            # Find weekly cohort rows
            weekly_cohorts = []
            
            # Look for rows that contain date ranges like "28/04/2025 - 04/05/2025"
            for row_idx, row in enumerate(all_values):
                for col_idx, cell in enumerate(row):
                    cell_str = str(cell).strip()
                    if ' - ' in cell_str and ('2025' in cell_str or '2024' in cell_str):
                        # Check if this is a weekly cohort row starting from 28/04/2025
                        if '28/04/2025' in cell_str or any(month in cell_str for month in 
                                                         ['05/2025', '06/2025', '07/2025', '08/2025', 
                                                          '09/2025', '10/2025', '11/2025', '12/2025']):
                            weekly_cohorts.append({
                                'row_idx': row_idx,
                                'date_range': cell_str,
                                'col_idx': col_idx
                            })
                            logger.info(f"Found weekly cohort: {cell_str} at row {row_idx}, col {col_idx}")
            
            if not weekly_cohorts:
                logger.warning("No weekly cohorts found starting from 28/04/2025")
                return {'raw_data': {}, 'weekly_data': []}
            
            # Extract data for each weekly cohort
            weekly_data = []
            velocity_metrics = []
            
            for cohort in weekly_cohorts:
                row_idx = cohort['row_idx']
                date_range = cohort['date_range']
                
                # Look for the data row (usually the next row after the cohort header)
                data_row_idx = row_idx + 1
                if data_row_idx < len(all_values):
                    data_row = all_values[data_row_idx]
                    
                    week_data = {'week_range': date_range}
                    
                    # Extract velocity metrics from specific columns
                    metrics = {
                        'lead_to_sql': self._safe_extract_float(data_row, 3),      # Column D
                        'lead_to_ms': self._safe_extract_float(data_row, 4),       # Column E
                        'ms_to_1st_meeting': self._safe_extract_float(data_row, 5), # Column F
                        'ms_to_mc': self._safe_extract_float(data_row, 6),         # Column G
                        'mc_to_closed': self._safe_extract_float(data_row, 7),     # Column H
                        'lead_to_win': self._safe_extract_float(data_row, 8)       # Column I
                    }
                    
                    week_data.update(metrics)
                    weekly_data.append(week_data)
                    
                    # Collect metrics for averaging
                    velocity_metrics.append(metrics)
            
            # Calculate averages
            averages = {}
            if velocity_metrics:
                for metric in ['lead_to_sql', 'lead_to_ms', 'ms_to_1st_meeting', 
                              'ms_to_mc', 'mc_to_closed', 'lead_to_win']:
                    values = [m[metric] for m in velocity_metrics if m[metric] > 0]
                    averages[f"{metric}_avg"] = sum(values) / len(values) if values else 0
            
            logger.info(f"Batch processed velocity data: {len(weekly_data)} weeks")
            return {
                'raw_data': averages,
                'weekly_data': weekly_data
            }
            
        except Exception as e:
            logger.error(f"Error in process_velocity_data_batch: {e}")
            return {'raw_data': {}, 'weekly_data': []}
    
    def _extract_cell_value(self, cell_data):
        """Extract numeric value from cell data returned by batch_get"""
        try:
            if cell_data and len(cell_data) > 0 and len(cell_data[0]) > 0:
                value = cell_data[0][0]
                if value and str(value).strip():
                    # Remove commas and convert to float
                    clean_value = str(value).replace(',', '').strip()
                    return float(clean_value)
            return 0
        except (ValueError, TypeError, IndexError):
            return 0
    
    def _safe_extract_float(self, row, col_idx):
        """Safely extract float value from row at given column index"""
        try:
            if len(row) > col_idx:
                value = row[col_idx]
                if value and str(value).strip():
                    clean_value = str(value).replace(',', '').strip()
                    return float(clean_value)
            return 0
        except (ValueError, TypeError):
            return 0

    def find_latest_data_column(self, sheet_id, worksheet_name):
        """Find the latest column with data based on row 1 headers - DEPRECATED"""
        logger.warning("find_latest_data_column is deprecated, use batch operations instead")
        return 'V'  # Default fallback
    
    def get_weekly_sales_velocity_data(self, sheet_id, worksheet_name=None):
        """Get weekly Sales Velocity data - DEPRECATED, use batch operations instead"""
        logger.warning("get_weekly_sales_velocity_data is deprecated, use process_velocity_data_batch instead")
        return []
    
    def is_week_after_start_date(self, week_range, start_date_str):
        """Check if a week range is after the start date - DEPRECATED"""
        logger.warning("is_week_after_start_date is deprecated")
        return True
    
    def safe_float_convert(self, value):
        """Safely convert a value to float - DEPRECATED, use _safe_extract_float instead"""
        return self._safe_extract_float([value], 0) if value else 0
    
    def get_batch_cell_values(self, worksheet, cell_ranges_dict):
        """Get multiple cell values in a single batch request - DEPRECATED"""
        logger.warning("get_batch_cell_values is deprecated, use batch_get_all_sheet_data instead")
        try:
            cell_values_list = worksheet.batch_get(list(cell_ranges_dict.values()))
            data = {}
            metric_keys = list(cell_ranges_dict.keys())
            for i, value_list in enumerate(cell_values_list):
                metric = metric_keys[i]
                data[metric] = self._extract_cell_value(value_list)
            return data
        except Exception as e:
            logger.error(f"Error in deprecated get_batch_cell_values: {e}")
            return {metric: 0 for metric in cell_ranges_dict.keys()}
    
    def get_cell_value(self, sheet_id, worksheet_name, cell_range):
        """Get value from a specific cell - DEPRECATED, use batch operations instead"""
        logger.warning("get_cell_value is deprecated, use batch operations instead")
        return 0
    
    def _process_vip_data_batch(self, worksheet):
        """Process VIP data using batch operations"""
        return self.process_vip_data_batch(worksheet)
    
    def _process_velocity_data_batch(self, worksheet):
        """Process velocity data using batch operations"""
        return self.process_velocity_data_batch(worksheet)
    
    def _process_funnel_data_batch(self, worksheet, sheet_key):
        """Process funnel data using batch operations"""
        return self.process_funnel_data_batch(worksheet, sheet_key)
    
    def _process_membership_data_batch(self, worksheet):
        """Process membership data using batch operations"""
        return self.process_membership_data_batch(worksheet)

    # Legacy methods - kept for backward compatibility but now use batch operations
    def _process_vip_data(self, worksheet, config):
        """Process VIP data for a worksheet - now uses batch operations"""
        return self.process_vip_data_batch(worksheet)
    
    def _process_velocity_data(self, worksheet, config):
        """Process velocity data for a worksheet - now uses batch operations"""
        return self.process_velocity_data_batch(worksheet)
    
    def _process_funnel_data(self, worksheet, config):
        """Process funnel data for a worksheet - now uses batch operations"""
        # Get the sheet_key from the config
        sheet_key = None
        for key, sheet_config in GOOGLE_SHEETS_CONFIG['sheets'].items():
            if sheet_config.get('id') == config.get('id') and sheet_config.get('worksheet_name') == config.get('worksheet_name'):
                sheet_key = key
                break
        
        if not sheet_key:
            logger.error(f"Could not find sheet_key for config: {config}")
            return {'raw_data': {}, 'table_data': []}
        
        return self.process_funnel_data_batch(worksheet, sheet_key)
    
    def _process_membership_data(self, worksheet, config):
        """Process membership data for a worksheet - now uses batch operations"""
        return self.process_membership_data_batch(worksheet)

    # Remove old individual methods that are no longer needed
    def get_monthly_vip_data_for_worksheet(self, worksheet):
        """Legacy method - now uses batch operations"""
        return self.process_vip_data_batch(worksheet).get('monthly_data', {})
    
    def get_monthly_membership_data_for_worksheet(self, worksheet):
        """Legacy method - now uses batch operations"""
        return self.process_membership_data_batch(worksheet).get('monthly_data', {})
    
    def parse_weekly_velocity_data(self, worksheet):
        """Legacy method - now uses batch operations"""
        result = self.process_velocity_data_batch(worksheet)
        return {
            'averages': result.get('raw_data', {}),
            'weekly_data': result.get('weekly_data', [])
        }
    
    def get_sheet_data(self, sheet_key):
        """Get all configured data from a specific sheet, routing to the correct parser."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Apply rate limiting
                self._rate_limit_delay()
                
                sheet_config = GOOGLE_SHEETS_CONFIG['sheets'][sheet_key]
                sheet_id = sheet_config['id']
                worksheet_name = sheet_config.get('worksheet_name')
                category = sheet_config.get('category', 'unknown')

                logger.info(f"Processing {sheet_key}: sheet_id={sheet_id}, worksheet={worksheet_name}, category={category}")

                if not sheet_id:
                    logger.warning(f"No sheet ID configured for {sheet_key}")
                    return {}

                # Cache the result for 1 hour to reduce API calls
                cache_key = f"sheet_data_{sheet_id}_{worksheet_name}_{category}"
                cached_data = self._get_cached_data(cache_key, allow_expired=False)
                if cached_data:
                    logger.info(f"Using cached data for {sheet_key}")
                    return cached_data
                
                # Add delay between requests to avoid rate limiting
                self._rate_limit_delay()
                
                try:
                    # Get the worksheet
                    worksheet = self._get_worksheet(sheet_id, worksheet_name)
                    if not worksheet:
                        logger.warning(f"Could not access worksheet {worksheet_name} in sheet {sheet_id}")
                        return None
                    
                    # Process data based on category
                    if category == 'vip':
                        data = self._process_vip_data_batch(worksheet)
                    elif category == 'velocity':
                        data = self._process_velocity_data_batch(worksheet)
                    elif category == 'funnel':
                        data = self._process_funnel_data_batch(worksheet, sheet_key)
                    elif category == 'membership':
                        data = self._process_membership_data_batch(worksheet)
                    else:
                        logger.warning(f"Unknown category: {category}")
                        return None
                    
                    # Cache the result for 1 hour
                    self._cache_data(cache_key, data, CACHE_DURATION)
                    return data
                    
                except Exception as e:
                    logger.error(f"API Error in get_sheet_data for {sheet_key}: {e}")
                    # Try to get cached data as fallback
                    cached_data = self._get_cached_data(cache_key, allow_expired=True)
                    if cached_data:
                        logger.info(f"Using cached data (possibly expired) as fallback for {sheet_key}")
                        return cached_data
                    return None

            except gspread.exceptions.WorksheetNotFound:
                logger.error(f"Worksheet '{worksheet_name}' not found in sheet '{sheet_id}' for key '{sheet_key}'.")
                return {}
            except gspread.exceptions.APIError as e:
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    self._record_error('RATE_LIMIT', str(e))
                    logger.warning(f"⚠️ API rate limit exceeded for {worksheet_name}")
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                    else:
                        logger.error(f"❌ Max retries exceeded for {worksheet_name} due to rate limiting")
                else:
                    self._record_error('API_ERROR', str(e))
                logger.error(f"❌ API Error in get_sheet_data for {sheet_key}: {e}")
                return {}
            except Exception as e:
                self._record_error('GENERAL_ERROR', str(e))
                logger.error(f"An unexpected error occurred in get_sheet_data for {sheet_key}: {e}")
                return {}
        
        return {}

    def get_all_sheets_data_batch(self):
        """
        Optimized method to get data from all configured sheets using batch operations.
        This dramatically reduces API calls by batching requests per sheet.
        """
        # Clear any previous errors
        self._clear_errors()
        
        all_data = {}
        
        # Group sheets by their sheet_id to minimize API calls
        sheets_by_id = {}
        for sheet_key, sheet_config in GOOGLE_SHEETS_CONFIG['sheets'].items():
            sheet_id = sheet_config['id']
            if sheet_id not in sheets_by_id:
                sheets_by_id[sheet_id] = []
            sheets_by_id[sheet_id].append((sheet_key, sheet_config))
        
        logger.info(f"Processing {len(sheets_by_id)} unique sheets with batch operations")
        
        for sheet_id, sheet_configs in sheets_by_id.items():
            try:
                # Apply rate limiting per sheet
                self._rate_limit_delay()
                
                # Process each worksheet in this sheet
                for sheet_key, sheet_config in sheet_configs:
                    try:
                        worksheet_name = sheet_config.get('worksheet_name')
                        category = sheet_config.get('category', 'unknown')
                        
                        logger.info(f"Batch processing {sheet_key}: category={category}, worksheet={worksheet_name}")
                        
                        # Check cache first
                        cache_key = f"sheet_data_{sheet_id}_{worksheet_name}_{category}"
                        cached_data = self._get_cached_data(cache_key, allow_expired=False)
                        if cached_data:
                            logger.info(f"Using cached data for {sheet_key}")
                            all_data[sheet_key] = {
                                'config': sheet_config,
                                'name': sheet_config.get('name', 'Unnamed Sheet'),
                                **cached_data
                            }
                            continue
                        
                        # Get worksheet
                        worksheet = self._get_worksheet(sheet_id, worksheet_name)
                        if not worksheet:
                            logger.warning(f"Could not access worksheet {worksheet_name} in sheet {sheet_id}")
                            all_data[sheet_key] = {
                                'config': sheet_config,
                                'name': sheet_config.get('name', 'Unnamed Sheet'),
                                'raw_data': {},
                                'monthly_data': {},
                                'weekly_data': []
                            }
                            continue
                        
                        # Process data using batch operations based on category
                        if category == 'vip':
                            data = self.process_vip_data_batch(worksheet)
                        elif category == 'velocity':
                            data = self.process_velocity_data_batch(worksheet)
                        elif category == 'funnel':
                            data = self.process_funnel_data_batch(worksheet, sheet_key)
                        elif category == 'membership':
                            data = self.process_membership_data_batch(worksheet)
                        else:
                            logger.warning(f"Unknown category: {category}")
                            data = {'raw_data': {}, 'monthly_data': {}, 'weekly_data': []}
                        
                        # Structure the data as the processor expects it
                        all_data[sheet_key] = {
                            'config': sheet_config,
                            'name': sheet_config.get('name', 'Unnamed Sheet'),
                            **data
                        }
                        
                        # Cache the result
                        self._cache_data(cache_key, data, CACHE_DURATION)
                        
                        logger.info(f"Successfully batch processed {sheet_key}")
                        
                    except Exception as e:
                        logger.error(f"Failed to batch process {sheet_key}: {e}")
                        # Add empty structure for failed sheets
                        all_data[sheet_key] = {
                            'config': sheet_config,
                            'name': sheet_config.get('name', 'Unnamed Sheet'),
                            'raw_data': {},
                            'monthly_data': {},
                            'weekly_data': []
                        }
                
            except Exception as e:
                logger.error(f"Failed to process sheet {sheet_id}: {e}")
                # Add empty structures for all sheets in this sheet_id
                for sheet_key, sheet_config in sheet_configs:
                    if sheet_key not in all_data:
                        all_data[sheet_key] = {
                            'config': sheet_config,
                            'name': sheet_config.get('name', 'Unnamed Sheet'),
                            'raw_data': {},
                            'monthly_data': {},
                            'weekly_data': []
                        }
        
        logger.info(f"Batch processing completed for {len(all_data)} sheets")
        return all_data

    def get_all_sheets_data(self):
        """
        Get data from all configured sheets and structure it for the processor.
        Now uses optimized batch operations.
        """
        return self.get_all_sheets_data_batch()

    def test_connection(self):
        """Test connection to Google Sheets"""
        try:
            if not self.client:
                return False, "Client not initialized"
            
            first_sheet_key = list(GOOGLE_SHEETS_CONFIG['sheets'].keys())[0]
            sheet_config = GOOGLE_SHEETS_CONFIG['sheets'][first_sheet_key]
            
            if not sheet_config['id']:
                return False, "No sheet ID configured"
            
            self.client.open_by_key(sheet_config['id'])
            return True, "Connection successful"
            
        except Exception as e:
            return False, f"Connection failed: {e}"

    def _get_cached_data(self, cache_key, allow_expired=False):
        """Get cached data if available and not expired"""
        cache_file = f"cache/{cache_key}.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    if allow_expired or time.time() - cached['timestamp'] < CACHE_DURATION:
                        return cached['data']
            except Exception as e:
                logger.warning(f"Error reading cache file {cache_file}: {e}")
        return None
    
    def _cache_data(self, cache_key, data, duration):
        """Cache data with timestamp"""
        os.makedirs('cache', exist_ok=True)
        cache_file = f"cache/{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump({
                    'data': data,
                    'timestamp': time.time(),
                    'duration': duration
                }, f)
        except Exception as e:
            logger.warning(f"Error writing cache file {cache_file}: {e}")
    
    def clear_old_cache(self):
        """Clear cache files older than 24 hours"""
        cache_dir = 'cache'
        if not os.path.exists(cache_dir):
            return
        
        current_time = time.time()
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    if current_time - os.path.getmtime(filepath) > 86400:  # 24 hours
                        os.remove(filepath)
                        logger.info(f"Removed old cache file: {filename}")
                except Exception as e:
                    logger.warning(f"Error removing cache file {filename}: {e}")
    
    def clear_all_cache(self):
        """Clear all cache files"""
        cache_dir = 'cache'
        if not os.path.exists(cache_dir):
            return
        
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    os.remove(filepath)
                    logger.info(f"Removed cache file: {filename}")
                except Exception as e:
                    logger.warning(f"Error removing cache file {filename}: {e}")

    def _get_worksheet(self, sheet_id, worksheet_name):
        """Get a worksheet by ID and name with proper rate limiting"""
        try:
            # Apply rate limiting before making API call
            self._rate_limit_delay()
            
            sheet = self.client.open_by_key(sheet_id)
            if worksheet_name:
                return sheet.worksheet(worksheet_name)
            else:
                return sheet.sheet1
        except Exception as e:
            logger.error(f"Error getting worksheet {worksheet_name} from sheet {sheet_id}: {e}")
            return None

    # Performance monitoring methods
    def get_performance_stats(self):
        """Get performance statistics for the batch operations"""
        return {
            'request_delay': self.REQUEST_DELAY,
            'last_request_time': self.last_api_call_time,
            'cache_duration': CACHE_DURATION
        }
    
    def log_batch_performance(self, operation_name, start_time, num_ranges=0, num_sheets=0):
        """Log performance metrics for batch operations"""
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Batch {operation_name} completed in {duration:.2f}s - "
                   f"Ranges: {num_ranges}, Sheets: {num_sheets}, "
                   f"Avg per range: {duration/max(num_ranges, 1):.3f}s") 

    def test_batch_operations(self):
        """
        Test method to validate batch operations and compare performance.
        Returns a detailed report of the batch operations performance.
        """
        test_results = {
            'success': False,
            'performance': {},
            'errors': [],
            'sheets_processed': 0,
            'total_api_calls': 0,
            'cache_hits': 0
        }
        
        try:
            logger.info("Starting batch operations test...")
            start_time = time.time()
            
            # Clear cache to ensure fresh test
            self.clear_all_cache()
            
            # Test batch data fetching
            all_data = self.get_all_sheets_data_batch()
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # Analyze results
            sheets_processed = len(all_data)
            successful_sheets = sum(1 for data in all_data.values() 
                                  if data.get('raw_data') or data.get('monthly_data') or data.get('weekly_data'))
            
            # Estimate API calls saved
            # Old method: ~5-10 calls per sheet (header + individual cells)
            # New method: ~1-2 calls per sheet (batch operations)
            estimated_old_calls = sheets_processed * 7  # Conservative estimate
            estimated_new_calls = sheets_processed * 2  # Batch operations
            calls_saved = estimated_old_calls - estimated_new_calls
            
            test_results.update({
                'success': successful_sheets > 0,
                'performance': {
                    'total_duration': total_duration,
                    'sheets_processed': sheets_processed,
                    'successful_sheets': successful_sheets,
                    'avg_time_per_sheet': total_duration / max(sheets_processed, 1),
                    'estimated_api_calls_old': estimated_old_calls,
                    'estimated_api_calls_new': estimated_new_calls,
                    'api_calls_saved': calls_saved,
                    'performance_improvement': f"{(calls_saved / estimated_old_calls * 100):.1f}%" if estimated_old_calls > 0 else "N/A"
                },
                'sheets_processed': sheets_processed,
                'data_summary': {}
            })
            
            # Analyze data quality
            for sheet_key, data in all_data.items():
                category = data.get('config', {}).get('category', 'unknown')
                has_data = bool(data.get('raw_data') or data.get('monthly_data') or data.get('weekly_data'))
                
                test_results['data_summary'][sheet_key] = {
                    'category': category,
                    'has_data': has_data,
                    'raw_data_keys': list(data.get('raw_data', {}).keys()),
                    'monthly_data_count': len(data.get('monthly_data', {})),
                    'weekly_data_count': len(data.get('weekly_data', []))
                }
            
            logger.info(f"Batch operations test completed successfully in {total_duration:.2f}s")
            logger.info(f"Processed {sheets_processed} sheets, {successful_sheets} successful")
            logger.info(f"Estimated API calls saved: {calls_saved} ({test_results['performance']['performance_improvement']})")
            
        except Exception as e:
            test_results['errors'].append(str(e))
            logger.error(f"Batch operations test failed: {e}")
        
        return test_results
    
    def benchmark_vs_old_method(self, sheet_key):
        """
        Benchmark the new batch method against a simulated old method for a single sheet.
        This is for performance comparison purposes.
        """
        if sheet_key not in GOOGLE_SHEETS_CONFIG['sheets']:
            return {'error': f'Sheet key {sheet_key} not found'}
        
        sheet_config = GOOGLE_SHEETS_CONFIG['sheets'][sheet_key]
        category = sheet_config.get('category')
        
        try:
            # Clear cache for fair comparison
            cache_key = f"sheet_data_{sheet_config['id']}_{sheet_config.get('worksheet_name')}_{category}"
            cache_file = f"cache/{cache_key}.json"
            if os.path.exists(cache_file):
                os.remove(cache_file)
            
            # Get worksheet
            worksheet = self._get_worksheet(sheet_config['id'], sheet_config.get('worksheet_name'))
            if not worksheet:
                return {'error': 'Could not access worksheet'}
            
            # Benchmark new batch method
            start_time = time.time()
            if category == 'vip':
                batch_result = self.process_vip_data_batch(worksheet)
            elif category == 'membership':
                batch_result = self.process_membership_data_batch(worksheet)
            elif category == 'funnel':
                batch_result = self.process_funnel_data_batch(worksheet, sheet_key)
            elif category == 'velocity':
                batch_result = self.process_velocity_data_batch(worksheet)
            else:
                return {'error': f'Unknown category: {category}'}
            
            batch_time = time.time() - start_time
            
            return {
                'sheet_key': sheet_key,
                'category': category,
                'batch_method': {
                    'duration': batch_time,
                    'data_points': len(batch_result.get('monthly_data', {})),
                    'has_data': bool(batch_result.get('raw_data') or batch_result.get('monthly_data') or batch_result.get('weekly_data'))
                },
                'performance_notes': 'Batch method uses single API call vs multiple individual calls'
            }
            
        except Exception as e:
            return {'error': str(e)}

    def _record_error(self, error_type, error_message):
        """Record the last error for debugging purposes"""
        self.last_error_type = error_type
        self.last_error_message = error_message
        logger.error(f"Recorded error - Type: {error_type}, Message: {error_message}")
    
    def _clear_errors(self):
        """Clear recorded errors"""
        self.last_error_type = None
        self.last_error_message = None
    
    def get_last_error_info(self):
        """Get information about the last error"""
        return {
            'error_type': self.last_error_type,
            'error_message': self.last_error_message,
            'is_rate_limit': self.last_error_type == 'RATE_LIMIT'
        } 