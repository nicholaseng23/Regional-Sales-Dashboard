import pandas as pd
import numpy as np
from config import METRICS_CONFIG, GOOGLE_SHEETS_CONFIG
import logging
from collections import defaultdict
import re
from datetime import datetime
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        pass
    
    def calculate_metric(self, data_dict, metric_key):
        metric_config = METRICS_CONFIG[metric_key]
        formula = metric_config['formula']
        
        # Extract variable names from the formula (e.g., 'total_deals', 'onsite_vip')
        variables = re.findall(r'[a-zA-Z_]\w*', formula)
        
        # Create a safe environment for eval(), providing 0 for any missing data
        safe_env = {var: data_dict.get(var, 0) for var in variables}

        # Add a check for division by zero before evaluation
        try:
            # Check for division operation
            if '/' in formula:
                # Simplistic check: find the denominator. 
                # Assumes formula is in 'numerator / denominator' format.
                denominator_str = formula.split('/')[-1].strip()
                if '(' in denominator_str: # Handle cases like '... / (var1 + var2)'
                    denominator_str = denominator_str.replace('(', '').replace(')', '')
                
                # Evaluate the denominator expression separately
                denominator_val = eval(denominator_str, {}, safe_env)
                
                if denominator_val == 0:
                    return 0.0 # Return 0 to prevent division by zero error

            return eval(formula, {"__builtins__": {}}, safe_env)
        except (NameError, SyntaxError) as e:
            logging.error(f"Error evaluating formula for '{metric_key}': {e}. Env: {safe_env}")
            return None # Indicates an error in the formula or data
        except Exception as e:
            logging.error(f"An unexpected error occurred calculating metric '{metric_key}': {e}")
            return None
    
    def process_sheet_data(self, raw_data, category):
        processed_data = {'raw_data': raw_data, 'metrics': {}}
        if not raw_data: # Ensure raw_data is not empty
            return processed_data

        for metric_key, metric_info in METRICS_CONFIG.items():
            if metric_info['category'] == category:
                metric_value = self.calculate_metric(raw_data, metric_key)
                processed_data['metrics'][metric_key] = {
                    'value': metric_value,
                    'format': metric_info.get('format', '{}'),
                    'description': metric_info.get('description', '')
                }
        return processed_data
    
    def process_all_data(self, all_sheets_data):
        """Process data from all sheets and return consolidated metrics."""
        processed_data = {}
        for sheet_key, sheet_info in all_sheets_data.items():
            sheet_config = GOOGLE_SHEETS_CONFIG['sheets'].get(sheet_key, {})
            sheet_category = sheet_config.get('category', 'general')
            
            # The data from the client is in sheet_info['data']
            data_from_client = sheet_info.get('data', {})

            # Standardize the structure for processing
            raw_data = data_from_client.get('raw_data', {})
            weekly_data = data_from_client.get('weekly_data', [])

            processed_data[sheet_key] = {
                'name': sheet_info['name'],
                'category': sheet_category,
                'raw_data': raw_data,
                'weekly_data': weekly_data,
                'metrics': self.process_sheet_data(raw_data, sheet_category)
            }
        return processed_data
    
    def calculate_regional_totals_by_category(self, processed_data, category):
        """Calculate and aggregate regional totals for a specific category."""
        regional_totals = {}
        
        # Define initial structures for each category
        if category == 'vip':
            regional_totals = {'total_deals': 0, 'onsite_vip': 0, 'remote_vip': 0}
        elif category == 'funnel':
            regional_totals = {'leads': 0, 'qualified_leads': 0, 'opportunities': 0, 'proposals': 0, 'negotiations': 0, 'closed_won': 0, 'closed_lost': 0}
        elif category == 'velocity':
            regional_totals = {'lead_to_sql_avg': [], 'lead_to_ms_avg': [], 'ms_to_1st_meeting_avg': [], 'ms_to_mc_avg': [], 'mc_to_closed_avg': [], 'lead_to_win_avg': [], 'weekly_data': []}
        elif category == 'membership':
            regional_totals = {'total_deals': 0, 'membership_1': 0, 'membership_2': 0}

        # Aggregate data from all sheets in the category
        for sheet_key, sheet_info in processed_data.items():
            if sheet_info.get('category') == category:
                raw_data = sheet_info.get('raw_data', {})
                for key in regional_totals:
                    if key == 'weekly_data':
                        regional_totals[key].extend(sheet_info.get('weekly_data', []))
                    elif isinstance(regional_totals[key], list):
                        if raw_data.get(key, 0) > 0: regional_totals[key].append(raw_data.get(key, 0))
                    else:
                        regional_totals[key] += raw_data.get(key, 0)
        
        # Post-process for averages if it's the velocity category
        if category == 'velocity':
            final_velocity_totals = {'weekly_data': regional_totals['weekly_data']}
            for key, values in regional_totals.items():
                if key != 'weekly_data' and isinstance(values, list):
                    final_velocity_totals[key] = np.mean(values) if values else 0
            regional_totals = final_velocity_totals

        # Calculate metrics based on the aggregated totals
        regional_metrics = {}
        for metric_key, metric_config in METRICS_CONFIG.items():
            if metric_config.get('category') == category:
                regional_metrics[metric_key] = self.calculate_metric(regional_totals, metric_key)
        
        return {'totals': regional_totals, 'metrics': regional_metrics}
    
    def get_summary_stats(self, all_sheets_data):
        """Get summary statistics for the dashboard organized by category."""
        summary = {'total_countries': len(all_sheets_data), 'categories': {}}
        
        for category in ['vip', 'funnel', 'velocity', 'membership']:
            category_summary = {'country_breakdown': {}}
            
            # Aggregate country data for the current category
            for sheet_key, sheet_info in all_sheets_data.items():
                if sheet_info.get('category') == category:
                    category_summary['country_breakdown'][sheet_key] = {
                        'name': sheet_info['name'],
                        'metrics': sheet_info.get('metrics', {})
                    }
            
            # Calculate regional totals and metrics for the category
            regional_data = self.calculate_regional_totals_by_category(all_sheets_data, category)
            category_summary.update({
                'regional_totals': regional_data['totals'],
                'regional_metrics': regional_data['metrics'],
            })
            
            summary['categories'][category] = category_summary
            
        return summary
    
    def calculate_regional_totals(self, countries_data, category):
        regional_totals = defaultdict(float)
        
        if category == 'velocity':
            all_weekly_data = []
            for country_data in countries_data.values():
                if country_data and 'raw_data' in country_data and 'weekly_data' in country_data['raw_data']:
                    all_weekly_data.extend(country_data['raw_data']['weekly_data'])
            
            regional_totals['weekly_data'] = all_weekly_data
            if all_weekly_data:
                num_weeks = len(all_weekly_data)
                avg_keys = [k for k in all_weekly_data[0].keys() if k != 'week_range']
                for key in avg_keys:
                    total = sum(float(d.get(key, 0)) for d in all_weekly_data)
                    regional_totals[f"{key}_avg"] = total / num_weeks if num_weeks > 0 else 0
            return dict(regional_totals)

        for country_data in countries_data.values():
            if country_data and 'raw_data' in country_data:
                for key, value in country_data['raw_data'].items():
                    if isinstance(value, (int, float)):
                        regional_totals[key] += value
        return dict(regional_totals)

    def prepare_dashboard_data(self, all_sheets_data):
        """
        Processes all raw data from sheets and transforms it into a structured
        dictionary perfect for rendering the dashboard UI.
        """
        
        # 1. Initialize the final data structure
        dashboard_data = {
            'vip': {'regional': {'monthly_data': {}}, 'countries': {}},
            'funnel': {'regional': {'metrics': {}}, 'countries': {}},
            'velocity': {'regional': {'metrics': {}, 'weekly_data': []}, 'countries': {}},
            'membership': {'regional': {'monthly_data': {}}, 'countries': {}}
        }

        # 2. Process each sheet and populate the country-level data
        for sheet_key, data in all_sheets_data.items():
            config = data.get('config', {})
            category = config.get('category')
            
            # Extract country code with better fallback logic
            country = config.get('country')
            if not country:
                # Fallback: extract from sheet key (e.g., 'vip_dashboard_my' -> 'MY')
                if '_' in sheet_key:
                    country = sheet_key.split('_')[-1].upper()
                else:
                    country = sheet_key.upper()
            
            raw_data = data.get('raw_data', {})

            if not category:
                continue

            # Initialize country data if not exists
            if country not in dashboard_data[category]['countries']:
                if category == 'vip':
                    dashboard_data[category]['countries'][country] = {'monthly_data': {}}
                elif category == 'funnel':
                    dashboard_data[category]['countries'][country] = {'metrics': {}, 'table_data': []}
                elif category == 'velocity':
                    dashboard_data[category]['countries'][country] = {'metrics': {}, 'weekly_data': []}
                elif category == 'membership':
                    dashboard_data[category]['countries'][country] = {'monthly_data': {}}

            # Calculate metrics for the individual sheet
            metrics = self.calculate_all_metrics_for_category(raw_data, category)
            
            if category == 'vip':
                dashboard_data['vip']['countries'][country]['metrics'] = metrics
                monthly_data = data.get('monthly_data', {})
                
                # Calculate percentages for each month in country data
                for month, month_data in monthly_data.items():
                    total_deals = month_data.get('total_deals', 0)
                    onsite_vip_deals = month_data.get('onsite_vip_deals', 0)
                    remote_vip_deals = month_data.get('remote_vip_deals', 0)
                    
                    month_data['onsite_vip_percentage'] = (onsite_vip_deals / total_deals * 100) if total_deals > 0 else 0
                    month_data['remote_vip_percentage'] = (remote_vip_deals / total_deals * 100) if total_deals > 0 else 0
                    month_data['total_vip_percentage'] = month_data['onsite_vip_percentage'] + month_data['remote_vip_percentage']
                    # Remove column reference from month label
                    month_data['month_label'] = f"{datetime.strptime(month, '%B %Y').strftime('%B')}"
                
                dashboard_data['vip']['countries'][country]['monthly_data'] = monthly_data
            elif category == 'funnel':
                dashboard_data['funnel']['countries'][country]['metrics'] = metrics
                # Add table data for Sales Funnel
                table_data = data.get('table_data', [])
                dashboard_data['funnel']['countries'][country]['table_data'] = table_data
            elif category == 'velocity':
                dashboard_data['velocity']['countries'][country]['metrics'] = metrics
                dashboard_data['velocity']['countries'][country]['weekly_data'] = data.get('weekly_data', [])
            elif category == 'membership':
                dashboard_data['membership']['countries'][country]['metrics'] = metrics
                monthly_data = data.get('monthly_data', {})
                
                # Calculate membership attachment rates for each month in country data
                for month, month_data in monthly_data.items():
                    total_deals = month_data.get('total_deals', 0)
                    membership_1 = month_data.get('membership_1', 0)
                    membership_2 = month_data.get('membership_2', 0)
                    
                    month_data['membership_attachment_rate'] = ((membership_1 + membership_2) / total_deals * 100) if total_deals > 0 else 0
                    # Remove column reference from month label
                    month_data['month_label'] = f"{datetime.strptime(month, '%B %Y').strftime('%B')}"
                
                dashboard_data['membership']['countries'][country]['monthly_data'] = monthly_data

        # 3. Aggregate country data to create regional totals
        self.aggregate_regional_data(dashboard_data)
        
        return dashboard_data

    def calculate_all_metrics_for_category(self, data_dict, category):
        """Calculates all applicable metrics for a given data dictionary and category."""
        metrics = {}
        for metric_key, metric_info in METRICS_CONFIG.items():
            if metric_info.get('category') == category:
                value = self.calculate_metric(data_dict, metric_key)
                metrics[metric_key] = {
                    'value': value,
                    'format': metric_info.get('format', '{}'),
                    'description': metric_info.get('description', '')
                }
        return metrics

    def aggregate_regional_data(self, dashboard_data):
        """Aggregates country-level data to the regional level in-place."""
        
        # --- Aggregate VIP Data ---
        regional_vip_monthly = {}
        for country_data in dashboard_data['vip']['countries'].values():
            for month, month_data in country_data.get('monthly_data', {}).items():
                if month not in regional_vip_monthly:
                    regional_vip_monthly[month] = {
                        'total_deals': 0,
                        'onsite_vip_deals': 0,
                        'remote_vip_deals': 0
                    }
                regional_vip_monthly[month]['total_deals'] += month_data.get('total_deals', 0)
                regional_vip_monthly[month]['onsite_vip_deals'] += month_data.get('onsite_vip_deals', 0)
                regional_vip_monthly[month]['remote_vip_deals'] += month_data.get('remote_vip_deals', 0)
        
        # Recalculate percentages and add month labels for regional VIP
        for month, data in regional_vip_monthly.items():
            total_deals = data['total_deals']
            data['onsite_vip_percentage'] = (data['onsite_vip_deals'] / total_deals * 100) if total_deals > 0 else 0
            data['remote_vip_percentage'] = (data['remote_vip_deals'] / total_deals * 100) if total_deals > 0 else 0
            data['total_vip_percentage'] = data['onsite_vip_percentage'] + data['remote_vip_percentage']
            data['month_label'] = f"{datetime.strptime(month, '%B %Y').strftime('%B')}"

        dashboard_data['vip']['regional']['monthly_data'] = dict(sorted(regional_vip_monthly.items(), key=lambda item: datetime.strptime(item[0], '%B %Y'), reverse=True))

        # --- Aggregate Velocity Data ---
        all_country_weeks = []
        for country_data in dashboard_data['velocity']['countries'].values():
            all_country_weeks.extend(country_data.get('weekly_data', []))
        
        if all_country_weeks:
            df = pd.DataFrame(all_country_weeks)
            # Group by week range and average the metrics
            # The data needs to be numeric for this
            for col in df.columns:
                if col != 'week_range':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            regional_weekly_df = df.groupby('week_range').mean().reset_index()
            dashboard_data['velocity']['regional']['weekly_data'] = regional_weekly_df.to_dict('records')
            
            # Calculate overall regional averages
            regional_velocity_metrics = {}
            for col in regional_weekly_df.columns:
                if col != 'week_range':
                    avg_val = regional_weekly_df[col].mean()
                    metric_key = f"{col}_avg"
                    regional_velocity_metrics[metric_key] = {
                        'value': avg_val,
                        'format': '{:.1f}',
                        'description': f"{col.replace('_', ' ').title()} Average"
                    }
            dashboard_data['velocity']['regional']['metrics'] = regional_velocity_metrics

        # --- Aggregate Membership Data ---
        regional_membership_monthly = {}
        for country_data in dashboard_data['membership']['countries'].values():
            for month, month_data in country_data.get('monthly_data', {}).items():
                if month not in regional_membership_monthly:
                    regional_membership_monthly[month] = {
                        'total_deals': 0,
                        'membership_1': 0,
                        'membership_2': 0
                    }
                regional_membership_monthly[month]['total_deals'] += month_data.get('total_deals', 0)
                regional_membership_monthly[month]['membership_1'] += month_data.get('membership_1', 0)
                regional_membership_monthly[month]['membership_2'] += month_data.get('membership_2', 0)
        
        # Recalculate membership attachment rates and add month labels for regional membership
        for month, data in regional_membership_monthly.items():
            total_deals = data['total_deals']
            data['membership_attachment_rate'] = ((data['membership_1'] + data['membership_2']) / total_deals * 100) if total_deals > 0 else 0
            data['month_label'] = f"{datetime.strptime(month, '%B %Y').strftime('%B')}"

        dashboard_data['membership']['regional']['monthly_data'] = dict(sorted(regional_membership_monthly.items(), key=lambda item: datetime.strptime(item[0], '%B %Y'), reverse=True))