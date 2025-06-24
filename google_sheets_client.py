import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import streamlit as st
from config import GOOGLE_SHEETS_CONFIG
import logging
import time
import re
from datetime import datetime, timedelta
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DURATION = 3600  # Increased from 14400 to 3600 (1 hour cache)
REQUEST_DELAY = 2.0  # Increased from 1.0 to 2.0 seconds between requests
MAX_RETRIES = 2  # Reduced from 3 to 2 to fail faster

class GoogleSheetsClient:
    def __init__(self):
        self.client = None
        self.request_delay = REQUEST_DELAY
        self.last_request_time = 0
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize Google Sheets client with service account credentials"""
        try:
            # Define the scope
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            # Load credentials
            credentials = GOOGLE_SHEETS_CONFIG['credentials_file']
            
            if isinstance(credentials, dict):
                # Credentials provided as dictionary (from environment variable)
                creds = Credentials.from_service_account_info(
                    credentials, 
                    scopes=scope
                )
            elif isinstance(credentials, str) and os.path.exists(credentials):
                # Credentials provided as file path
                creds = Credentials.from_service_account_file(
                    credentials, 
                    scopes=scope
                )
            else:
                raise Exception("Invalid credentials format")
            
            # Create client
            self.client = gspread.authorize(creds)
            logger.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            st.error(f"Failed to connect to Google Sheets: {e}")
    
    def _rate_limit_delay(self):
        """Implement rate limiting to prevent API quota exhaustion."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Ensure minimum delay between requests
        if time_since_last < self.request_delay:
            sleep_time = self.request_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def exponential_backoff(self, attempt):
        """Implement exponential backoff for rate limiting"""
        delay = min(3 ** attempt, 120)  # Max 120 seconds (increased from 60)
        time.sleep(delay)
        logger.info(f"Rate limited, waiting {delay} seconds (attempt {attempt})")
    
    def find_latest_data_column(self, sheet_id, worksheet_name):
        """Find the latest column with data based on row 1 headers"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if not self.client:
                    raise Exception("Google Sheets client not initialized")
                
                sheet = self.client.open_by_key(sheet_id)
                worksheet = sheet.worksheet(worksheet_name) if worksheet_name else sheet.sheet1
                
                # Get all values from row 1 to find the latest month
                row_1_values = worksheet.row_values(1)
                
                # Look for date patterns like "25-05" (May 2025)
                date_pattern = r'\d{2}-\d{2}'
                latest_col_index = None
                latest_date = None
                
                for i, cell_value in enumerate(row_1_values):
                    if cell_value and re.search(date_pattern, str(cell_value)):
                        # Convert index to column letter
                        col_letter = chr(65 + i) if i < 26 else chr(65 + i // 26 - 1) + chr(65 + i % 26)
                        latest_col_index = i + 1  # 1-based indexing
                        latest_date = cell_value
                        logger.info(f"Found date column: {cell_value} at column {col_letter}")
                
                if latest_col_index:
                    # Convert to column letter (A=1, B=2, ..., Z=26, AA=27, etc.)
                    if latest_col_index <= 26:
                        return chr(64 + latest_col_index)  # A-Z
                    else:
                        # For columns beyond Z (AA, AB, etc.)
                        first_letter = chr(64 + (latest_col_index - 1) // 26)
                        second_letter = chr(65 + (latest_col_index - 1) % 26)
                        return first_letter + second_letter
                
                # Fallback to column V if no date pattern found
                logger.warning(f"No date pattern found in row 1, using default column V")
                return 'V'
                
            except Exception as e:
                if "429" in str(e) or "RATE_LIMIT_EXCEEDED" in str(e):
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                logger.error(f"Error finding latest data column: {e}")
                return 'V'  # Fallback to column V
        
        return 'V'  # Final fallback
    
    def get_weekly_sales_velocity_data(self, sheet_id, worksheet_name=None):
        """Get weekly Sales Velocity data starting from 28/04/2025"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if not self.client:
                    raise Exception("Google Sheets client not initialized")
                
                sheet = self.client.open_by_key(sheet_id)
                worksheet = sheet.worksheet(worksheet_name) if worksheet_name else sheet.sheet1
                
                # Get all data from the sheet to find weekly ranges
                # Assuming the data starts from row 2 and we need to find date ranges
                all_values = worksheet.get_all_values()
                
                if not all_values:
                    return []
                
                headers = all_values[0] if all_values else []
                weekly_data = []
                
                # Find columns for our metrics
                metric_columns = {
                    'week_range': None,
                    'lead_to_sql': None,
                    'lead_to_ms': None,
                    'ms_to_1st_meeting': None,
                    'ms_to_mc': None,
                    'mc_to_closed': None,
                    'lead_to_win': None
                }
                
                # Map headers to our metrics (you may need to adjust these based on actual headers)
                for i, header in enumerate(headers):
                    header_lower = header.lower()
                    if 'week' in header_lower or 'date' in header_lower:
                        metric_columns['week_range'] = i
                    elif 'lead to sql' in header_lower or 'lead_to_sql' in header_lower:
                        metric_columns['lead_to_sql'] = i
                    elif 'lead to ms' in header_lower or 'lead_to_ms' in header_lower:
                        metric_columns['lead_to_ms'] = i
                    elif 'ms to 1st meeting' in header_lower or 'ms_to_1st_meeting' in header_lower:
                        metric_columns['ms_to_1st_meeting'] = i
                    elif 'ms to mc' in header_lower or 'ms_to_mc' in header_lower:
                        metric_columns['ms_to_mc'] = i
                    elif 'mc to closed' in header_lower or 'mc_to_closed' in header_lower:
                        metric_columns['mc_to_closed'] = i
                    elif 'lead to win' in header_lower or 'lead_to_win' in header_lower:
                        metric_columns['lead_to_win'] = i
                
                # Process rows starting from row 2 (index 1)
                for row_idx, row in enumerate(all_values[1:], start=2):
                    if len(row) <= max(filter(None, metric_columns.values())):
                        continue
                    
                    week_range = row[metric_columns['week_range']] if metric_columns['week_range'] is not None else f"Week {row_idx-1}"
                    
                    # Check if this week is from 28/04/2025 onwards
                    if self.is_week_after_start_date(week_range, "28/04/2025"):
                        week_data = {
                            'week_range': week_range,
                            'lead_to_sql': self.safe_float_convert(row[metric_columns['lead_to_sql']] if metric_columns['lead_to_sql'] is not None else 0),
                            'lead_to_ms': self.safe_float_convert(row[metric_columns['lead_to_ms']] if metric_columns['lead_to_ms'] is not None else 0),
                            'ms_to_1st_meeting': self.safe_float_convert(row[metric_columns['ms_to_1st_meeting']] if metric_columns['ms_to_1st_meeting'] is not None else 0),
                            'ms_to_mc': self.safe_float_convert(row[metric_columns['ms_to_mc']] if metric_columns['ms_to_mc'] is not None else 0),
                            'mc_to_closed': self.safe_float_convert(row[metric_columns['mc_to_closed']] if metric_columns['mc_to_closed'] is not None else 0),
                            'lead_to_win': self.safe_float_convert(row[metric_columns['lead_to_win']] if metric_columns['lead_to_win'] is not None else 0)
                        }
                        weekly_data.append(week_data)
                
                # Add delay to avoid rate limiting
                time.sleep(2)
                return weekly_data
                
            except Exception as e:
                if "429" in str(e) or "RATE_LIMIT_EXCEEDED" in str(e):
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                logger.error(f"Error getting weekly sales velocity data: {e}")
                return []
        
        return []
    
    def is_week_after_start_date(self, week_range, start_date_str):
        """Check if a week range is after the start date (28/04/2025)"""
        try:
            # Parse start date
            start_date = datetime.strptime(start_date_str, "%d/%m/%Y")
            
            # Extract date from week range (assuming format like "28/04/2025 - 04/05/2025")
            if " - " in week_range:
                week_start_str = week_range.split(" - ")[0].strip()
                week_start = datetime.strptime(week_start_str, "%d/%m/%Y")
                return week_start >= start_date
            
            return True  # If we can't parse, include it
        except:
            return True  # If we can't parse, include it
    
    def safe_float_convert(self, value):
        """Safely convert a value to float"""
        try:
            return float(value) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def get_batch_cell_values(self, worksheet, cell_ranges_dict):
        """Get multiple cell values in a single batch request from a worksheet object."""
        try:
            cell_values_list = worksheet.batch_get(list(cell_ranges_dict.values()))
            
            data = {}
            metric_keys = list(cell_ranges_dict.keys())
            for i, value_list in enumerate(cell_values_list):
                metric = metric_keys[i]
                if value_list and value_list[0]:
                    value = value_list[0][0]
                    try:
                        # Convert to float, handling empty strings and commas
                        if value and str(value).strip():
                            # Remove commas and convert to float
                            clean_value = str(value).replace(',', '').strip()
                            data[metric] = float(clean_value)
                        else:
                            data[metric] = 0
                    except (ValueError, TypeError):
                        # If conversion fails, set to 0 instead of keeping as string
                        logger.warning(f"Could not convert '{value}' to number for {metric}, setting to 0")
                        data[metric] = 0
                else:
                    data[metric] = 0
            return data

        except Exception as e:
            logger.error(f"Error in get_batch_cell_values for worksheet '{worksheet.title}': {e}")
            return {metric: 0 for metric in cell_ranges_dict.keys()}
    
    def get_cell_value(self, sheet_id, worksheet_name, cell_range):
        """Get value from a specific cell in a Google Sheet worksheet"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                if not self.client:
                    raise Exception("Google Sheets client not initialized")
                
                # Open the spreadsheet
                sheet = self.client.open_by_key(sheet_id)
                
                # Get the specific worksheet by name
                if worksheet_name:
                    worksheet = sheet.worksheet(worksheet_name)
                else:
                    worksheet = sheet.sheet1  # Use first worksheet by default
                
                # Get cell value
                value = worksheet.acell(cell_range).value
                
                # Convert to numeric if possible
                try:
                    return float(value) if value else 0
                except (ValueError, TypeError):
                    return value if value else 0
                    
            except Exception as e:
                if "429" in str(e) or "RATE_LIMIT_EXCEEDED" in str(e):
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                logger.error(f"Error getting cell value from {sheet_id}, worksheet {worksheet_name}, {cell_range}: {e}")
                return 0
        
        return 0
    
    def parse_weekly_velocity_data(self, worksheet):
        """Parse weekly Sales Velocity data starting from 28/04/2025"""
        try:
            # Get all data from the worksheet
            all_values = worksheet.get_all_values()
            
            if not all_values:
                logger.warning("No data found in Sales Velocity worksheet")
                return {'weekly_data': [], 'averages': {}}
            
            logger.info(f"Sales Velocity sheet has {len(all_values)} rows")
            
            # Find weekly cohort rows
            weekly_cohorts = []
            
            # Look for rows that contain date ranges like "28/04/2025 - 04/05/2025"
            for row_idx, row in enumerate(all_values):
                for col_idx, cell in enumerate(row):
                    cell_str = str(cell).strip()
                    if ' - ' in cell_str and ('2025' in cell_str or '2024' in cell_str):
                        # Check if this is a weekly cohort row
                        if '28/04/2025' in cell_str or any(month in cell_str for month in ['05/2025', '06/2025', '07/2025', '08/2025', '09/2025', '10/2025', '11/2025', '12/2025']):
                            weekly_cohorts.append({
                                'row_idx': row_idx,
                                'date_range': cell_str,
                                'col_idx': col_idx
                            })
                            logger.info(f"Found weekly cohort: {cell_str} at row {row_idx}, col {col_idx}")
            
            if not weekly_cohorts:
                logger.warning("No weekly cohorts found starting from 28/04/2025")
                return {'weekly_data': [], 'averages': {}}
            
            # Extract data for each weekly cohort
            weekly_data = []
            
            for cohort in weekly_cohorts:
                row_idx = cohort['row_idx']
                date_range = cohort['date_range']
                
                # Based on your description, data is in specific rows:
                # For 28/04/2025 cohort: row 5 (D5, I5)
                # For 05/05/2025 cohort: row 4 (D4, I4)
                
                # Determine the data row based on the date range
                if '28/04/2025' in date_range:
                    data_row_idx = 4  # Row 5 (0-indexed = 4)
                    logger.info(f"Using row 5 for 28/04/2025 cohort")
                elif '05/05/2025' in date_range:
                    data_row_idx = 3  # Row 4 (0-indexed = 3)
                    logger.info(f"Using row 4 for 05/05/2025 cohort")
                else:
                    # For other weeks, try the row below the header
                    data_row_idx = row_idx + 1
                    logger.info(f"Using row {data_row_idx + 1} for {date_range}")
                
                if data_row_idx >= len(all_values):
                    logger.warning(f"Data row {data_row_idx} is out of bounds")
                    continue
                
                data_row = all_values[data_row_idx]
                logger.info(f"Data row {data_row_idx + 1}: {data_row}")
                
                week_data = {'week_range': date_range}
                
                # Extract values for each metric based on your specific cell mappings
                # Lead to SQL: Column D (index 3)
                # Lead to MS: Column E (index 4)
                # MS to 1st Meeting: Column F (index 5)
                # MS to MC: Column G (index 6)
                # MC to Closed: Column H (index 7)
                # Lead to Win: Column I (index 8)
                
                # Lead to SQL (Column D)
                if len(data_row) > 3:
                    cell_value = data_row[3]  # Column D
                    try:
                        numeric_value = float(cell_value) if cell_value and str(cell_value).strip() != '' else 0
                        week_data['lead_to_sql'] = numeric_value
                        logger.info(f"Extracted Lead to SQL: {numeric_value} from D{data_row_idx + 1}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse Lead to SQL value '{cell_value}'")
                        week_data['lead_to_sql'] = 0
                else:
                    week_data['lead_to_sql'] = 0
                
                # Lead to MS (Column E)
                if len(data_row) > 4:
                    cell_value = data_row[4]  # Column E
                    try:
                        numeric_value = float(cell_value) if cell_value and str(cell_value).strip() != '' else 0
                        week_data['lead_to_ms'] = numeric_value
                        logger.info(f"Extracted Lead to MS: {numeric_value} from E{data_row_idx + 1}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse Lead to MS value '{cell_value}'")
                        week_data['lead_to_ms'] = 0
                else:
                    week_data['lead_to_ms'] = 0
                
                # MS to 1st Meeting (Column F)
                if len(data_row) > 5:
                    cell_value = data_row[5]  # Column F
                    try:
                        numeric_value = float(cell_value) if cell_value and str(cell_value).strip() != '' else 0
                        week_data['ms_to_1st_meeting'] = numeric_value
                        logger.info(f"Extracted MS to 1st Meeting: {numeric_value} from F{data_row_idx + 1}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse MS to 1st Meeting value '{cell_value}'")
                        week_data['ms_to_1st_meeting'] = 0
                else:
                    week_data['ms_to_1st_meeting'] = 0
                
                # MS to MC (Column G)
                if len(data_row) > 6:
                    cell_value = data_row[6]  # Column G
                    try:
                        numeric_value = float(cell_value) if cell_value and str(cell_value).strip() != '' else 0
                        week_data['ms_to_mc'] = numeric_value
                        logger.info(f"Extracted MS to MC: {numeric_value} from G{data_row_idx + 1}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse MS to MC value '{cell_value}'")
                        week_data['ms_to_mc'] = 0
                else:
                    week_data['ms_to_mc'] = 0
                
                # MC to Closed (Column H)
                if len(data_row) > 7:
                    cell_value = data_row[7]  # Column H
                    try:
                        numeric_value = float(cell_value) if cell_value and str(cell_value).strip() != '' else 0
                        week_data['mc_to_closed'] = numeric_value
                        logger.info(f"Extracted MC to Closed: {numeric_value} from H{data_row_idx + 1}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse MC to Closed value '{cell_value}'")
                        week_data['mc_to_closed'] = 0
                else:
                    week_data['mc_to_closed'] = 0
                
                # Lead to Win (Column I)
                if len(data_row) > 8:
                    cell_value = data_row[8]  # Column I
                    try:
                        numeric_value = float(cell_value) if cell_value and str(cell_value).strip() != '' else 0
                        week_data['lead_to_win'] = numeric_value
                        logger.info(f"Extracted Lead to Win: {numeric_value} from I{data_row_idx + 1}")
                    except (ValueError, TypeError):
                        logger.warning(f"Could not parse Lead to Win value '{cell_value}'")
                        week_data['lead_to_win'] = 0
                else:
                    week_data['lead_to_win'] = 0
                
                weekly_data.append(week_data)
                logger.info(f"Added week data: {week_data}")
            
            # Calculate averages
            averages = {}
            if weekly_data:
                metrics = ['lead_to_sql', 'lead_to_ms', 'ms_to_1st_meeting', 'ms_to_mc', 'mc_to_closed', 'lead_to_win']
                for metric in metrics:
                    values = [week.get(metric, 0) for week in weekly_data if week.get(metric, 0) > 0]
                    averages[f'{metric}_avg'] = sum(values) / len(values) if values else 0
            
            logger.info(f"Parsed {len(weekly_data)} weeks of Sales Velocity data")
            logger.info(f"Calculated averages: {averages}")
            
            return {
                'weekly_data': weekly_data,
                'averages': averages
            }
            
        except Exception as e:
            logger.error(f"Error parsing weekly velocity data: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return {'weekly_data': [], 'averages': {}}
    
    def get_monthly_vip_data_for_worksheet(self, worksheet):
        """Fetch VIP data for all available months from a given worksheet object."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 1. Find all month columns from the header row (row 1)
                header_row = worksheet.row_values(1)
                month_columns = {}
                date_pattern = r'(\d{2})-(\d{2})' # Pattern for 'YY-MM'
                
                for i, cell_value in enumerate(header_row):
                    match = re.search(date_pattern, str(cell_value))
                    if match:
                        year, month = match.groups()
                        month_name = datetime(int(f"20{year}"), int(month), 1).strftime("%B %Y")
                        column_letter = chr(65 + i)
                        month_columns[month_name] = column_letter
                
                if not month_columns:
                    logger.warning(f"No month columns found in {worksheet.title}")
                    return {}

                # 2. Batch fetch all required data for all months
                ranges_to_fetch = []
                for col in month_columns.values():
                    ranges_to_fetch.extend([f"{col}2", f"{col}28", f"{col}30"])
                
                cell_values = worksheet.batch_get(ranges_to_fetch, major_dimension='COLUMNS')
                
                # 3. Process the fetched data
                monthly_data = {}
                cell_index = 0
                for month, col in month_columns.items():
                    try:
                        total_deals_col = cell_values[cell_index]
                        onsite_vip_col = cell_values[cell_index+1]
                        remote_vip_col = cell_values[cell_index+2]

                        total_deals = float(total_deals_col[0][0]) if total_deals_col and total_deals_col[0] else 0
                        onsite_vip = float(onsite_vip_col[0][0]) if onsite_vip_col and onsite_vip_col[0] else 0
                        remote_vip = float(remote_vip_col[0][0]) if remote_vip_col and remote_vip_col[0] else 0
                        
                        monthly_data[month] = {
                            'total_deals': total_deals,
                            'onsite_vip_deals': onsite_vip,
                            'remote_vip_deals': remote_vip,
                            'month_label': f"{datetime.strptime(month, '%B %Y').strftime('%B')} ({col})"
                        }
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Could not parse data for month {month} in {worksheet.title}: {e}")
                    
                    cell_index += 3
                
                return monthly_data

            except gspread.exceptions.APIError as e:
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                logger.error(f"API Error fetching monthly VIP data for {worksheet.title}: {e}")
                return {}
            except Exception as e:
                logger.error(f"An unexpected error occurred in get_monthly_vip_data_for_worksheet: {e}")
                return {}
        return {}
    
    def get_monthly_membership_data_for_worksheet(self, worksheet):
        """Fetch membership data for all available months from a given worksheet object."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 1. Find all month columns from the header row (row 1)
                header_row = worksheet.row_values(1)
                month_columns = {}
                date_pattern = r'(\d{2})-(\d{2})' # Pattern for 'YY-MM'
                
                for i, cell_value in enumerate(header_row):
                    match = re.search(date_pattern, str(cell_value))
                    if match:
                        year, month = match.groups()
                        month_name = datetime(int(f"20{year}"), int(month), 1).strftime("%B %Y")
                        column_letter = chr(65 + i)
                        month_columns[month_name] = column_letter
                
                if not month_columns:
                    logger.warning(f"No month columns found in {worksheet.title}")
                    return {}

                # 2. Batch fetch all required data for all months
                ranges_to_fetch = []
                for col in month_columns.values():
                    ranges_to_fetch.append(f"{col}2")  # Total deals
                    # For Thailand, we need V30, V31 instead of V43, V44
                    if worksheet.title == 'TH':
                        ranges_to_fetch.extend([f"{col}30", f"{col}31"])
                    else:
                        ranges_to_fetch.extend([f"{col}43", f"{col}44"])
                
                cell_values = worksheet.batch_get(ranges_to_fetch)
                
                # 3. Process the fetched data
                monthly_data = {}
                cell_index = 0
                for month, col in month_columns.items():
                    try:
                        total_deals_col = cell_values[cell_index]
                        membership_1_col = cell_values[cell_index+1]
                        membership_2_col = cell_values[cell_index+2]

                        total_deals = float(total_deals_col[0][0]) if total_deals_col and total_deals_col[0] else 0
                        membership_1 = float(membership_1_col[0][0]) if membership_1_col and membership_1_col[0] else 0
                        membership_2 = float(membership_2_col[0][0]) if membership_2_col and membership_2_col[0] else 0
                        
                        monthly_data[month] = {
                            'total_deals': total_deals,
                            'membership_1': membership_1,
                            'membership_2': membership_2,
                            'month_label': f"{datetime.strptime(month, '%B %Y').strftime('%B')} ({col})"
                        }
                    except (ValueError, TypeError, IndexError) as e:
                        logger.error(f"Could not parse data for month {month} in {worksheet.title}: {e}")
                    
                    cell_index += 3
                
                return monthly_data

            except gspread.exceptions.APIError as e:
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                logger.error(f"API Error fetching monthly membership data for {worksheet.title}: {e}")
                return {}
            except Exception as e:
                logger.error(f"An unexpected error occurred in get_monthly_membership_data_for_worksheet: {e}")
                return {}
        return {}
    
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
                cached_data = self._get_cached_data(cache_key)
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
                        data = self._process_vip_data(worksheet, sheet_config)
                    elif category == 'velocity':
                        data = self._process_velocity_data(worksheet, sheet_config)
                    elif category == 'funnel':
                        data = self._process_funnel_data(worksheet, sheet_config)
                    elif category == 'membership':
                        data = self._process_membership_data(worksheet, sheet_config)
                    else:
                        logger.warning(f"Unknown category: {category}")
                        return None
                    
                    # Cache the result for 1 hour
                    self._cache_data(cache_key, data, CACHE_DURATION)
                    return data
                    
                except Exception as e:
                    logger.error(f"API Error in get_sheet_data for {sheet_key}: {e}")
                    # Try to get cached data as fallback
                    cached_data = self._get_cached_data(cache_key)
                    if cached_data:
                        logger.info(f"Using cached data as fallback for {sheet_key}")
                        return cached_data
                    return None

            except gspread.exceptions.WorksheetNotFound:
                logger.error(f"Worksheet '{worksheet_name}' not found in sheet '{sheet_id}' for key '{sheet_key}'.")
                return {}
            except gspread.exceptions.APIError as e:
                if "RATE_LIMIT_EXCEEDED" in str(e) or "429" in str(e):
                    if attempt < max_retries - 1:
                        self.exponential_backoff(attempt)
                        continue
                logger.error(f"API Error in get_sheet_data for {sheet_key}: {e}")
                return {}
            except Exception as e:
                logger.error(f"An unexpected error occurred in get_sheet_data for {sheet_key}: {e}")
                return {}
        
        return {}

    def get_all_sheets_data(self):
        """Get data from all configured sheets and structure it for the processor."""
        all_data = {}
        for sheet_key, sheet_config in GOOGLE_SHEETS_CONFIG['sheets'].items():
            try:
                sheet_data = self.get_sheet_data(sheet_key)
                # Structure the data as the processor expects it
                all_data[sheet_key] = {
                    'config': sheet_config,
                    'name': sheet_config.get('name', 'Unnamed Sheet'),
                    **sheet_data
                }
                # Rate limiting is already handled in get_sheet_data
            except Exception as e:
                logger.error(f"Failed to get data for {sheet_key}: {e}")
                # Add empty structure for failed sheets
                all_data[sheet_key] = {
                    'config': sheet_config,
                    'name': sheet_config.get('name', 'Unnamed Sheet'),
                    'raw_data': {},
                    'monthly_data': {},
                    'weekly_data': []
                }
        
        return all_data

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

    def get_sales_funnel_data(self, worksheet, sheet_key):
        """Get Sales Funnel data for all data points from specified ranges."""
        try:
            sheet_config = GOOGLE_SHEETS_CONFIG['sheets'][sheet_key]
            worksheet_name = sheet_config['worksheet_name']
            
            # Define the ranges for each country based on the configuration
            ranges_config = {
                'sales_funnel_my': {
                    'ranges': ['BE54:BS63', 'BE74:BS83', 'BE94:BS103'],
                },
                'sales_funnel_ph': {
                    'ranges': ['BD53:BT84'],
                },
                'sales_funnel_th': {
                    'ranges': ['BH47:BV78'],
                }
            }
            
            config = ranges_config.get(sheet_key)
            if not config:
                logger.error(f"No range configuration found for {sheet_key}")
                return {'raw_data': {}, 'table_data': []}
            
            # Get all data from the specified ranges
            all_data = []
            for range_str in config['ranges']:
                try:
                    range_data = worksheet.batch_get([range_str])
                    if range_data and range_data[0]:
                        all_data.extend(range_data[0])
                except Exception as e:
                    logger.warning(f"Could not fetch range {range_str}: {e}")
            
            if not all_data:
                logger.warning(f"No data found in ranges for {sheet_key}")
                return {'raw_data': {}, 'table_data': []}
            
            # Only keep rows that have enough columns
            filtered_data = [row for row in all_data if len(row) >= 14]
            
            # Filter out header rows and only extract columns 7,8,9,10,11,13,14,15 (0-based: 6,7,8,9,10,12,13,14)
            table_data = []
            for row in filtered_data:
                # Skip header rows (rows that contain header text)
                first_col = str(row[0]).strip() if row[0] else ""
                if any(header_keyword in first_col.lower() for header_keyword in ['status', 'timestamp', 'update', 'header', 'title', 'created date']):
                    continue
                
                # Skip rows that don't look like dates (too short or contain non-date patterns)
                if len(first_col) < 8 or not any(char.isdigit() for char in first_col):
                    continue
                
                table_row = {
                    'created_date': row[0],           # 1st column - actual date
                    'sum_of_won': row[6],            # 7th column
                    'lead_mql_pct': row[7],          # 8th column
                    'mql_sql_pct': row[8],           # 9th column
                    'sql_ms_pct': row[9],            # 10th column
                    'ms_mc_pct': row[10],            # 11th column
                    'lead_to_win_pct': row[13],      # 14th column
                    'lead_to_sql_pct': row[14],      # 15th column - Lead to SQL %
                }
                table_data.append(table_row)
            
            # Use the most recent data point for the main metrics (for backward compatibility)
            latest_data = table_data[-1] if table_data else {}
            
            logger.info(f"Sales Funnel data for {sheet_key}: {len(table_data)} data points (columns 7,8,9,10,11,13,14,15)")
            return {
                'raw_data': latest_data,
                'table_data': table_data
            }
            
        except Exception as e:
            logger.error(f"Error getting Sales Funnel data for {sheet_key}: {e}")
            return {'raw_data': {}, 'table_data': []} 

    def _process_vip_data(self, worksheet, config):
        """Process VIP data for a worksheet"""
        monthly_data = self.get_monthly_vip_data_for_worksheet(worksheet)
        sorted_months = dict(sorted(monthly_data.items(), key=lambda item: datetime.strptime(item[0], '%B %Y'), reverse=True))
        latest_month_data = list(sorted_months.values())[0] if sorted_months else {}
        return {
            'raw_data': latest_month_data,
            'monthly_data': sorted_months
        }
    
    def _process_velocity_data(self, worksheet, config):
        """Process velocity data for a worksheet"""
        parsed_data = self.parse_weekly_velocity_data(worksheet)
        return {
            'raw_data': parsed_data.get('averages', {}),
            'weekly_data': parsed_data.get('weekly_data', [])
        }
    
    def _process_funnel_data(self, worksheet, config):
        """Process funnel data for a worksheet"""
        logger.info(f"Fetching funnel data using new method")
        # Get the sheet_key from the config
        sheet_key = None
        for key, sheet_config in GOOGLE_SHEETS_CONFIG['sheets'].items():
            if sheet_config.get('id') == config.get('id') and sheet_config.get('worksheet_name') == config.get('worksheet_name'):
                sheet_key = key
                break
        
        if not sheet_key:
            logger.error(f"Could not find sheet_key for config: {config}")
            return {'raw_data': {}, 'table_data': []}
        
        return self.get_sales_funnel_data(worksheet, sheet_key)
    
    def _process_membership_data(self, worksheet, config):
        """Process membership data for a worksheet"""
        monthly_data = self.get_monthly_membership_data_for_worksheet(worksheet)
        sorted_months = dict(sorted(monthly_data.items(), key=lambda item: datetime.strptime(item[0], '%B %Y'), reverse=True))
        latest_month_data = list(sorted_months.values())[0] if sorted_months else {}
        return {
            'raw_data': latest_month_data,
            'monthly_data': sorted_months
        }
    
    def _get_cached_data(self, cache_key):
        """Get cached data if available and not expired"""
        cache_file = f"cache/{cache_key}.json"
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    if time.time() - cached['timestamp'] < CACHE_DURATION:
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
        """Get a worksheet by ID and name"""
        try:
            sheet = self.client.open_by_key(sheet_id)
            if worksheet_name:
                return sheet.worksheet(worksheet_name)
            else:
                return sheet.sheet1
        except Exception as e:
            logger.error(f"Error getting worksheet {worksheet_name} from sheet {sheet_id}: {e}")
            return None 