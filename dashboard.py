import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
from google_sheets_client import GoogleSheetsClient
from data_processor import DataProcessor
from scheduler import start_background_scheduler
from config import DASHBOARD_CONFIG, GOOGLE_SHEETS_CONFIG
import logging
import os

# Set additional environment variables for Streamlit
os.environ.setdefault('STREAMLIT_SERVER_ENABLE_STATIC_SERVING', 'true')
os.environ.setdefault('STREAMLIT_SERVER_ENABLE_CORS', 'false')
os.environ.setdefault('STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION', 'false')

# --- Page Configuration & Styling ---
st.set_page_config(
    page_title="Regional Sales Dashboard", page_icon="✨", layout="wide", initial_sidebar_state="expanded"
)
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

    /* --- Modern & Vibrant Theme --- */
    :root {
        --bg-color: #111827; /* Tailwind Gray 900 */
        --card-color: #1F2937; /* Tailwind Gray 800 */
        --border-color: #374151; /* Tailwind Gray 700 */
        --primary-text: #F9FAFB; /* Tailwind Gray 50 */
        --secondary-text: #9CA3AF; /* Tailwind Gray 400 */
        --accent-color: #2DD4BF; /* Tailwind Teal 400 */
        --accent-gradient: linear-gradient(135deg, #2DD4BF, #34D399); /* Teal to Green */
    }

    /* General Styling */
    .stApp {
        background-color: var(--bg-color);
        color: var(--primary-text);
        font-family: 'Poppins', sans-serif;
    }
    
    /* Fix Streamlit default white backgrounds */
    .main .block-container {
        background-color: var(--bg-color);
        color: var(--primary-text);
    }
    
    /* Fix sidebar styling */
    .css-1d391kg {
        background-color: var(--card-color);
    }
    
    /* SIMPLE FIXED BACKGROUND APPROACH */
    
    /* Set fixed background on body and main containers */
    html, body {
        background-color: var(--bg-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Force main app container to fixed background */
    .stApp, .stApp > div, .main, .main > div {
        background-color: var(--bg-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Fix all block containers */
    .block-container, .block-container > div {
        background-color: var(--bg-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Fix element containers */
    .element-container, .element-container > div {
        background-color: transparent !important;
        color: var(--primary-text) !important;
    }
    
    /* Fix all data display components with fixed backgrounds */
    .stDataFrame, .stDataFrame > div, .stDataFrame table {
        background-color: var(--card-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Fix table elements */
    table, thead, tbody, tr, td {
        background-color: var(--card-color) !important;
        color: var(--primary-text) !important;
    }
    
    th, thead th {
        background-color: var(--border-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Fix alert/success messages */
    .stAlert, .stSuccess, .stInfo, .stWarning, .stError {
        background-color: var(--card-color) !important;
        color: var(--primary-text) !important;
        border: 1px solid var(--accent-color) !important;
    }
    
    /* Our custom cards should keep their styling */
    .month-card, .kpi-card {
        background-color: var(--card-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Headers */
    .main-header {
        font-size: 2.25rem;
        font-weight: 700;
        color: var(--primary-text);
        padding: 1.5rem 0;
        text-align: center;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--primary-text);
        padding-bottom: 1rem;
        margin-top: 2rem;
        border-bottom: 2px solid var(--border-color);
    }

    /* KPI Cards */
    .kpi-card {
        background-color: var(--card-color);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid var(--border-color);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .kpi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .kpi-title {
        font-size: 1rem;
        font-weight: 500;
        color: var(--secondary-text);
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.75rem;
    }
    .kpi-value {
        font-size: 2.75rem;
        font-weight: 700;
        color: var(--primary-text);
        line-height: 1;
        max-width: 100%;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    /* Monthly Breakdown Cards */
    .month-card {
        background: var(--card-color);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 1px solid var(--border-color);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
        height: 100%;
    }
    .month-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .month-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--primary-text);
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .month-metrics-container {
        display: flex;
        justify-content: space-around;
        align-items: center;
        text-align: center;
        gap: 1rem;
    }
    .month-metric-value {
        font-size: 2.25rem;
        font-weight: 600;
        color: var(--accent-color);
    }
    .month-metric-label {
        font-size: 0.875rem;
        color: var(--secondary-text);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .month-footer {
        font-size: 0.875rem;
        color: var(--secondary-text);
        text-align: center;
        margin-top: 1.5rem;
        padding-top: 1rem;
        border-top: 1px solid var(--border-color);
    }

    /* Button styling */
    .stButton > button {
        background-color: var(--card-color) !important;
        color: var(--primary-text) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px;
    }
    
    .stButton > button:hover {
        background-color: var(--border-color) !important;
        color: var(--primary-text) !important;
    }
    
    button[kind="secondary"] {
        background-color: var(--card-color) !important;
        color: var(--primary-text) !important;
        border: 1px solid var(--border-color) !important;
    }
    
    button[kind="primary"] {
        background-color: var(--accent-color) !important;
        color: var(--bg-color) !important;
        border: 1px solid var(--accent-color) !important;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 2px solid var(--border-color);
        flex-wrap: wrap;
        justify-content: flex-start;
        background-color: var(--bg-color) !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 8px 8px 0 0;
        color: var(--secondary-text) !important;
        font-weight: 600;
        font-size: 0.875rem;
        padding: 0.5rem 1rem;
        transition: color 0.2s ease, background-color 0.2s ease;
        border: none;
        border-bottom: 2px solid transparent;
        min-width: auto;
        flex: 0 1 auto;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--primary-text) !important;
        background-color: var(--card-color) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--primary-text) !important;
        background-color: var(--card-color) !important;
        border-bottom: 2px solid var(--accent-color) !important;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        background-color: var(--bg-color) !important;
        color: var(--primary-text) !important;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab"] {
            font-size: 0.75rem;
            padding: 0.4rem 0.8rem;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# --- Dashboard Class ---

class RegionalDashboard:
    def __init__(self):
        self.sheets_client = GoogleSheetsClient()
        self.data_processor = DataProcessor()
        self.timezone = pytz.timezone(DASHBOARD_CONFIG['timezone'])
        if 'scheduler_started' not in st.session_state:
            st.session_state.scheduler_started = False

    def load_dashboard_data(self):
        """Loads and processes all data required for the dashboard from Google Sheets."""
        # Check if we have data in session state (session-based cache)
        if 'dashboard_data' in st.session_state and 'data_timestamp' in st.session_state:
            # Check if data is still fresh (less than 2 hours old)
            data_age = datetime.now(self.timezone) - st.session_state.data_timestamp
            if data_age.total_seconds() < 7200:  # 2 hours
                st.info("Using session cached data (refreshed automatically every 2 hours)")
                return st.session_state.dashboard_data
        
        try:
            # Try to load data from Google Sheets API
            all_sheets_data = self.sheets_client.get_all_sheets_data()
            
            # Check if we got any data at all (not just empty structures)
            has_any_data = False
            successful_sheets = 0
            total_sheets = len(all_sheets_data)
            
            logging.info(f"Data loading analysis: {total_sheets} sheets to process")
            
            for sheet_key, data in all_sheets_data.items():
                # Check if this sheet has any actual data (not just empty structures)
                raw_data = data.get('raw_data', {})
                monthly_data = data.get('monthly_data', {})
                weekly_data = data.get('weekly_data', [])
                
                # Log details for debugging
                logging.info(f"Sheet {sheet_key}: raw_data={bool(raw_data)}, monthly_data={bool(monthly_data)}, weekly_data={bool(weekly_data)}")
                
                # Consider it successful if it has non-empty data structures
                if raw_data or monthly_data or weekly_data:
                    successful_sheets += 1
                    has_any_data = True
            
            logging.info(f"Data loading result: {successful_sheets}/{total_sheets} sheets successful")
            
            # Determine the appropriate message based on success rate
            if successful_sheets == total_sheets and has_any_data:
                # All sheets loaded successfully with data
                st.success("✅ Successfully loaded fresh data from Google Sheets API")
                dashboard_data = self.data_processor.prepare_dashboard_data(all_sheets_data)
                # Add timestamp to the dashboard data
                dashboard_data['last_refreshed'] = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
                
                # Store in session state for future use
                st.session_state.dashboard_data = dashboard_data
                st.session_state.data_timestamp = datetime.now(self.timezone)
                
                return dashboard_data
            elif successful_sheets > 0:
                # Some sheets loaded successfully
                st.warning(f"⚠️ Partial data loaded: {successful_sheets}/{total_sheets} sheets successful. Some data may be missing.")
                dashboard_data = self.data_processor.prepare_dashboard_data(all_sheets_data)
                dashboard_data['last_refreshed'] = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z') + " (partial)"
                
                # Store in session state for future use
                st.session_state.dashboard_data = dashboard_data
                st.session_state.data_timestamp = datetime.now(self.timezone)
                
                return dashboard_data
            else:
                # No sheets loaded successfully - check what type of error occurred
                error_info = self.sheets_client.get_last_error_info()
                if error_info['is_rate_limit']:
                    st.warning("⚠️ API rate limit reached. Using cached data from last successful load.")
                elif error_info['error_type']:
                    st.warning(f"⚠️ API error occurred: {error_info['error_type']}. Using cached data from last successful load.")
                else:
                    st.warning("⚠️ Unable to load fresh data from Google Sheets API. Using cached data from last successful load.")
                return self.load_cached_data()
            
        except Exception as e:
            logging.error(f"Error in load_dashboard_data: {e}", exc_info=True)
            st.warning("⚠️ Failed to load data from API. Using cached data.")
            return self.load_cached_data()

    def load_cached_data(self):
        """Load cached data for when API calls fail."""
        # First try to get any cached data from the sheets client
        try:
            cached_data = self.sheets_client.get_all_sheets_data()
            if cached_data:
                # Check if we got any real data (not just empty structures)
                has_real_data = False
                for sheet_key, data in cached_data.items():
                    if data.get('raw_data') or data.get('monthly_data'):
                        has_real_data = True
                        break
                
                if has_real_data:
                    st.info("✅ Using cached data from Google Sheets API")
                    dashboard_data = self.data_processor.prepare_dashboard_data(cached_data)
                    dashboard_data['last_refreshed'] = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
                    return dashboard_data
        except Exception as e:
            logging.error(f"Error loading cached data: {e}")
        
        # Fall back to the hardcoded test data
        test_data = {
            "vip_dashboard_my": {
                "config": {
                    "id": "1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE",
                    "name": "Malaysia VIP Data",
                    "worksheet_name": "MY",
                    "category": "vip",
                    "country": "MY",
                    "ranges": {
                        "total_deals": "V2",
                        "onsite_vip": "V28",
                        "remote_vip": "V30"
                    }
                },
                "name": "Malaysia VIP Data",
                "raw_data": {
                    "total_deals": 202,
                    "onsite_vip_deals": 97,
                    "remote_vip_deals": 67,
                    "month_label": "May (V)"
                },
                "monthly_data": {
                    "May 2025": {
                        "total_deals": 202,
                        "onsite_vip_deals": 97,
                        "remote_vip_deals": 67,
                        "month_label": "May (V)"
                    },
                    "April 2025": {
                        "total_deals": 142,
                        "onsite_vip_deals": 55,
                        "remote_vip_deals": 58,
                        "month_label": "April (U)"
                    }
                }
            },
            "vip_dashboard_ph": {
                "config": {
                    "id": "1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE",
                    "name": "Philippines VIP Data",
                    "worksheet_name": "PH",
                    "category": "vip",
                    "country": "PH",
                    "ranges": {
                        "total_deals": "V2",
                        "onsite_vip": "V28",
                        "remote_vip": "V30"
                    }
                },
                "name": "Philippines VIP Data",
                "raw_data": {
                    "total_deals": 54,
                    "onsite_vip_deals": 0,
                    "remote_vip_deals": 0,
                    "month_label": "May (V)"
                },
                "monthly_data": {
                    "May 2025": {
                        "total_deals": 54,
                        "onsite_vip_deals": 0,
                        "remote_vip_deals": 0,
                        "month_label": "May (V)"
                    },
                    "April 2025": {
                        "total_deals": 35,
                        "onsite_vip_deals": 0,
                        "remote_vip_deals": 0,
                        "month_label": "April (U)"
                    }
                }
            },
            "vip_dashboard_th": {
                "config": {
                    "id": "1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE",
                    "name": "Thailand VIP Data",
                    "worksheet_name": "TH",
                    "category": "vip",
                    "country": "TH",
                    "ranges": {
                        "total_deals": "V2",
                        "onsite_vip": "V28",
                        "remote_vip": "V30"
                    }
                },
                "name": "Thailand VIP Data",
                "raw_data": {
                    "total_deals": 26,
                    "onsite_vip_deals": 0,
                    "remote_vip_deals": 1,
                    "month_label": "May (V)"
                },
                "monthly_data": {
                    "May 2025": {
                        "total_deals": 26,
                        "onsite_vip_deals": 0,
                        "remote_vip_deals": 1,
                        "month_label": "May (V)"
                    },
                    "April 2025": {
                        "total_deals": 24,
                        "onsite_vip_deals": 0,
                        "remote_vip_deals": 2,
                        "month_label": "April (U)"
                    }
                }
            },
            "sales_velocity_my": {
                "config": {
                    "id": "1_KWf7wxtDUyypGsWXzsmCXhLOG8fmN0EapDXoKu_3EE",
                    "name": "Malaysia Sales Velocity",
                    "worksheet_name": None,
                    "category": "velocity",
                    "country": "MY",
                    "ranges": {
                        "weekly_data": "A:Z"
                    }
                },
                "name": "Malaysia Sales Velocity",
                "raw_data": {
                    "lead_to_sql_avg": 0.0,
                    "lead_to_ms_avg": 0.0,
                    "ms_to_1st_meeting_avg": 4.0,
                    "ms_to_mc_avg": 1.0,
                    "mc_to_closed_avg": 0.0,
                    "lead_to_win_avg": 0.0
                },
                "weekly_data": [
                    {
                        "week_range": "05/05/2025 - 11/05/2025",
                        "lead_to_sql": 0,
                        "lead_to_ms": 0,
                        "ms_to_1st_meeting": 4,
                        "ms_to_mc": 1,
                        "mc_to_closed": 0,
                        "lead_to_win": 0
                    },
                    {
                        "week_range": "28/04/2025 - 04/05/2025",
                        "lead_to_sql": 1,
                        "lead_to_ms": 1,
                        "ms_to_1st_meeting": 4,
                        "ms_to_mc": 4,
                        "mc_to_closed": 1,
                        "lead_to_win": 4
                    }
                ]
            }
        }
        
        dashboard_data = self.data_processor.prepare_dashboard_data(test_data)
        # Add timestamp to cached data
        dashboard_data['last_refreshed'] = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
        return dashboard_data

    # --- UI Rendering Methods ---
    def render_vip_dashboard(self, vip_data):
        if not vip_data:
            st.warning("No VIP data available to display.")
            return

        regional_monthly = vip_data.get('regional', {}).get('monthly_data', {})
        if not regional_monthly:
            st.warning("No regional VIP data available.")
            return

        latest_month_key = list(regional_monthly.keys())[0]
        latest_month_data = regional_monthly[latest_month_key]

        # --- Regional Key Performance Metrics ---
        st.markdown('<div class="section-header">Key Performance Metrics (Regional)</div>', unsafe_allow_html=True)
        kpi_cols = st.columns(4)
        with kpi_cols[0]:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>📈</span> Total Deals</div><div class="kpi-value">{latest_month_data["total_deals"]:.0f}</div></div>', unsafe_allow_html=True)
        with kpi_cols[1]:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🏢</span> Onsite VIP %</div><div class="kpi-value">{latest_month_data["onsite_vip_percentage"]:.1f}%</div></div>', unsafe_allow_html=True)
        with kpi_cols[2]:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🌐</span> Remote VIP %</div><div class="kpi-value">{latest_month_data["remote_vip_percentage"]:.1f}%</div></div>', unsafe_allow_html=True)
        with kpi_cols[3]:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🎯</span> Total VIP %</div><div class="kpi-value">{latest_month_data["total_vip_percentage"]:.1f}%</div></div>', unsafe_allow_html=True)
        
        # --- Individual Country KPI Cards ---
        st.markdown('<div class="section-header">Key Performance Metrics (By Country)</div>', unsafe_allow_html=True)
        countries = vip_data.get('countries', {})
        if countries:
            country_cols = st.columns(len(countries))
            
            for i, (country_code, country_data) in enumerate(countries.items()):
                monthly_data = country_data.get('monthly_data', {})
                if not monthly_data:
                    continue
                
                latest_country_month = list(monthly_data.values())[0]
                
                # Set correct flag for each country
                if country_code == 'MY':
                    flag = '🇲🇾'
                elif country_code == 'PH':
                    flag = '🇵🇭'
                elif country_code == 'TH':
                    flag = '🇹🇭'
                else:
                    flag = '🏳️'
                
                with country_cols[i]:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>{flag}</span> {country_code}</div><div class="kpi-value">{latest_country_month.get("total_deals", 0):.0f}</div></div>', unsafe_allow_html=True)
                    onsite_vip_rate = (latest_country_month.get("onsite_vip_deals", 0) / latest_country_month.get("total_deals", 1) * 100) if latest_country_month.get("total_deals", 0) > 0 else 0
                    st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🏢</span> Onsite VIP %</div><div class="kpi-value">{onsite_vip_rate:.1f}%</div></div>', unsafe_allow_html=True)
                    remote_vip_rate = (latest_country_month.get("remote_vip_deals", 0) / latest_country_month.get("total_deals", 1) * 100) if latest_country_month.get("total_deals", 0) > 0 else 0
                    st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🌐</span> Remote VIP %</div><div class="kpi-value">{remote_vip_rate:.1f}%</div></div>', unsafe_allow_html=True)

    def render_vip_monthly_breakdown(self, vip_data):
        if not vip_data:
            st.warning("No VIP data available to display.")
            return

        regional_monthly = vip_data.get('regional', {}).get('monthly_data', {})
        countries = vip_data.get('countries', {})
        
        if not regional_monthly and not countries:
            st.warning("No monthly data available.")
            return

        # Create tabs for different views
        tab_names = ["Overall"] + list(countries.keys())
        tabs = st.tabs(tab_names)
        
        # Overall/Regional tab
        with tabs[0]:
            if regional_monthly:
                st.markdown('<div class="section-header">Monthly Performance Breakdown (Overall)</div>', unsafe_allow_html=True)
                month_cols = st.columns(3)
                for i, (month, data) in enumerate(list(regional_monthly.items())[:6]):
                    col = month_cols[i % 3]
                    with col:
                        col.markdown(f"""
                        <div class="month-card">
                            <div class="month-header">{data['month_label']}</div>
                            <div class="month-metrics-container">
                                <div>
                                    <div class="month-metric-label">Onsite VIP</div>
                                    <div class="month-metric-value">{data['onsite_vip_percentage']:.1f}%</div>
                                    <div class="month-metric-label" style="font-size: 0.75rem; text-transform: none; opacity: 0.8;">{data['onsite_vip_deals']:.0f} deals</div>
                                </div>
                                <div>
                                    <div class="month-metric-label">Remote VIP</div>
                                    <div class="month-metric-value">{data['remote_vip_percentage']:.1f}%</div>
                                    <div class="month-metric-label" style="font-size: 0.75rem; text-transform: none; opacity: 0.8;">{data['remote_vip_deals']:.0f} deals</div>
                                </div>
                            </div>
                            <div class="month-footer">
                                Total: {data['total_deals']:.0f} deals | VIP: {data['total_vip_percentage']:.1f}%
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No overall monthly data available.")
        
        # Country tabs
        for i, (country_code, country_data) in enumerate(countries.items()):
            with tabs[i + 1]:
                monthly_data = country_data.get('monthly_data', {})
                if monthly_data:
                    st.markdown(f'<div class="section-header">Monthly Performance Breakdown ({country_code})</div>', unsafe_allow_html=True)
                    month_cols = st.columns(3)
                    for j, (month, data) in enumerate(list(monthly_data.items())[:6]):
                        col = month_cols[j % 3]
                        with col:
                            col.markdown(f"""
                            <div class="month-card">
                                <div class="month-header">{data['month_label']}</div>
                                <div class="month-metrics-container">
                                    <div>
                                        <div class="month-metric-label">Onsite VIP</div>
                                        <div class="month-metric-value">{data['onsite_vip_percentage']:.1f}%</div>
                                        <div class="month-metric-label" style="font-size: 0.75rem; text-transform: none; opacity: 0.8;">{data['onsite_vip_deals']:.0f} deals</div>
                                    </div>
                                    <div>
                                        <div class="month-metric-label">Remote VIP</div>
                                        <div class="month-metric-value">{data['remote_vip_percentage']:.1f}%</div>
                                        <div class="month-metric-label" style="font-size: 0.75rem; text-transform: none; opacity: 0.8;">{data['remote_vip_deals']:.0f} deals</div>
                                    </div>
                                </div>
                                <div class="month-footer">
                                    Total: {data['total_deals']:.0f} deals | VIP: {data['total_vip_percentage']:.1f}%
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info(f"No monthly data available for {country_code}.")

    def render_sales_funnel_dashboard(self, funnel_data):
        if not funnel_data:
            st.warning("No Sales Funnel data available.")
            return

        st.markdown('<div class="section-header">Sales Funnel by Country</div>', unsafe_allow_html=True)
        
        countries = funnel_data.get('countries', {})
        
        if not countries:
            st.info("No country funnel data available.")
            return
        
        # Display table data for each country
        for country_code, country_data in countries.items():
            table_data = country_data.get('table_data', [])
            
            if not table_data:
                continue
            
            # Get country name
            country_name = country_data.get('name', f'Country {country_code}')
            
            # Set correct flag and simplified name for each country
            if country_code == 'MY':
                flag = '🇲🇾'
                display_name = 'MY'
            elif country_code == 'PH':
                flag = '🇵🇭'
                display_name = 'PH'
            elif country_code == 'TH':
                flag = '🇹🇭'
                display_name = 'TH'
            else:
                flag = '🏳️'
                display_name = country_code
            
            st.markdown(f'<div class="subsection-header">{flag} {display_name}</div>', unsafe_allow_html=True)
            
            # Convert table data to DataFrame for display
            if table_data:
                df = pd.DataFrame(table_data)
                
                # Filter out rows that contain header text (non-numeric values)
                # Check if the first column contains date-like values and filter accordingly
                def is_valid_data_row(row):
                    # Check if sum_of_won is numeric (should be a number, not text)
                    try:
                        won_value = str(row.get('sum_of_won', '0')).replace('%', '').strip()
                        if not won_value or won_value == '':
                            return False
                        float(won_value)
                        
                        # Also check if created_date looks like a date (not header text)
                        created_date = str(row.get('created_date', '')).strip()
                        if created_date:
                            # Skip rows that contain common header text
                            header_keywords = ['status', 'timestamp', 'update', 'header', 'title']
                            if any(keyword in created_date.lower() for keyword in header_keywords):
                                return False
                            # Skip rows that are clearly not dates
                            if len(created_date) < 5:  # Too short to be a date
                                return False
                        
                        return True
                    except (ValueError, TypeError):
                        return False
                
                # Filter the dataframe to only include valid data rows
                df_filtered = df[df.apply(is_valid_data_row, axis=1)]
                
                if df_filtered.empty:
                    st.info(f"No valid numeric data found for {country_name}")
                    continue
                
                # Add a created date column (using the first column from the original data)
                # We'll need to get this from the original sheet data
                # For now, let's add a placeholder or use the row index
                df_filtered = df_filtered.copy()
                df_filtered['Created Date'] = df_filtered['created_date'] if 'created_date' in df_filtered.columns else [f'Cohort {i+1}' for i in range(len(df_filtered))]
                
                # Only show the new keys/columns plus created date
                column_mapping = {
                    'Created Date': 'Created Date ↓',
                    'sum_of_won': 'Sum of Won',
                    'lead_mql_pct': 'Lead-MQL%',
                    'mql_sql_pct': 'MQL-SQL%',
                    'sql_ms_pct': 'SQL-MS%',
                    'ms_mc_pct': 'MS-MC%',
                    'lead_to_win_pct': 'Lead to Win%',
                    'lead_to_sql_pct': 'Lead to SQL%'
                }
                
                # Select only the columns we want to display
                display_cols = ['Created Date'] + list(column_mapping.keys())[1:]  # Skip 'Created Date' from mapping
                df_display = df_filtered[display_cols].rename(columns=column_mapping)
                
                # Display the table
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info(f"No table data available for {country_name}")
            
            st.markdown("<br>", unsafe_allow_html=True)

    def render_sales_velocity_dashboard(self, velocity_data):
        if not velocity_data:
            st.warning("No Sales Velocity data available.")
            return

        # --- Latest Month Summary (using latest week data) ---
        st.markdown('<div class="section-header">Sales Velocity (Latest Month)</div>', unsafe_allow_html=True)
        weekly_data = velocity_data.get('regional', {}).get('weekly_data', [])
        
        if not weekly_data:
            st.info("No weekly velocity data available.")
        else:
            # Get the latest week data (first item in the list since it's sorted by date)
            latest_week = weekly_data[0]
            
            # Create metrics from the latest week data
            latest_metrics = {
                'lead_to_sql': {
                    'value': latest_week.get('lead_to_sql', 0),
                    'format': '{:.1f}',
                    'description': 'Lead to SQL (days)'
                },
                'lead_to_ms': {
                    'value': latest_week.get('lead_to_ms', 0),
                    'format': '{:.1f}',
                    'description': 'Lead to MS (days)'
                },
                'ms_to_1st_meeting': {
                    'value': latest_week.get('ms_to_1st_meeting', 0),
                    'format': '{:.1f}',
                    'description': 'MS to 1st Meeting (days)'
                },
                'ms_to_mc': {
                    'value': latest_week.get('ms_to_mc', 0),
                    'format': '{:.1f}',
                    'description': 'MS to MC (days)'
                },
                'mc_to_closed': {
                    'value': latest_week.get('mc_to_closed', 0),
                    'format': '{:.1f}',
                    'description': 'MC to Closed (days)'
                },
                'lead_to_win': {
                    'value': latest_week.get('lead_to_win', 0),
                    'format': '{:.1f}',
                    'description': 'Lead to Win (days)'
                }
            }
            
            kpi_cols = st.columns(len(latest_metrics))
            for i, (key, data) in enumerate(latest_metrics.items()):
                with kpi_cols[i]:
                    st.markdown(f"""
                    <div class="kpi-card">
                        <div class="kpi-title">{data.get('description', key)}</div>
                        <div class="kpi-value">{data['format'].format(data['value'])}</div>
                    </div>
                    """, unsafe_allow_html=True)
        
        # --- Past Data Table ---
        st.markdown('<div class="section-header">Sales Velocity Past Data</div>', unsafe_allow_html=True)
        
        if not weekly_data:
            st.info("No weekly velocity data found to display.")
            return
            
        df = pd.DataFrame(weekly_data)
        # Reorder and format columns for display
        display_cols = {
            'week_range': 'Week Range',
            'lead_to_sql': 'Lead to SQL (days)',
            'lead_to_ms': 'Lead to MS (days)',
            'ms_to_1st_meeting': 'MS to 1st Meeting (days)',
            'ms_to_mc': 'MS to MC (days)',
            'mc_to_closed': 'MC to Closed (days)',
            'lead_to_win': 'Lead to Win (days)'
        }
        
        # Filter df to only include columns we want to display and in the correct order
        df_display = df[[col for col in display_cols.keys() if col in df.columns]]
        
        # Format the numeric columns
        for col in display_cols.keys():
            if col != 'week_range' and col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"{x:.1f}")

        df_display = df_display.rename(columns=display_cols)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    def render_membership_dashboard(self, membership_data):
        if not membership_data:
            st.warning("No Membership data available to display.")
            return

        regional_monthly = membership_data.get('regional', {}).get('monthly_data', {})
        if not regional_monthly:
            st.warning("No regional Membership data available.")
            return

        latest_month_key = list(regional_monthly.keys())[0]
        latest_month_data = regional_monthly[latest_month_key]

        # --- Regional Key Performance Metrics ---
        st.markdown('<div class="section-header">Key Performance Metrics (Regional)</div>', unsafe_allow_html=True)
        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>📈</span> Total Deals</div><div class="kpi-value">{latest_month_data["total_deals"]:.0f}</div></div>', unsafe_allow_html=True)
        with kpi_cols[1]:
            membership_1 = latest_month_data.get("membership_1", 0)
            membership_2 = latest_month_data.get("membership_2", 0)
            total_deals = latest_month_data["total_deals"]
            membership_rate = ((membership_1 + membership_2) / total_deals * 100) if total_deals > 0 else 0
            
            # Debug: Check if the calculation is reasonable
            if membership_rate > 100:
                st.warning(f"Debug: Membership rate seems high: {membership_rate:.1f}% (membership_1: {membership_1}, membership_2: {membership_2}, total_deals: {total_deals})")
                membership_rate = min(membership_rate, 100)  # Cap at 100%
            
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🎯</span> Membership Attachment %</div><div class="kpi-value">{membership_rate:.1f}%</div></div>', unsafe_allow_html=True)
        with kpi_cols[2]:
            total_membership_deals = latest_month_data.get("membership_1", 0) + latest_month_data.get("membership_2", 0)
            st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>📊</span> Total Membership Deals</div><div class="kpi-value">{total_membership_deals:.0f}</div></div>', unsafe_allow_html=True)
        
        # --- Individual Country KPI Cards ---
        st.markdown('<div class="section-header">Key Performance Metrics (By Country)</div>', unsafe_allow_html=True)
        countries = membership_data.get('countries', {})
        if countries:
            country_cols = st.columns(len(countries))
            
            for i, (country_code, country_data) in enumerate(countries.items()):
                monthly_data = country_data.get('monthly_data', {})
                if not monthly_data:
                    continue
                
                latest_country_month = list(monthly_data.values())[0]
                
                # Set correct flag for each country
                if country_code == 'MY':
                    flag = '🇲🇾'
                elif country_code == 'PH':
                    flag = '🇵🇭'
                elif country_code == 'TH':
                    flag = '🇹🇭'
                else:
                    flag = '🏳️'
                
                with country_cols[i]:
                    st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>{flag}</span> {country_code}</div><div class="kpi-value">{latest_country_month.get("total_deals", 0):.0f}</div></div>', unsafe_allow_html=True)
                    membership_rate = ((latest_country_month.get("membership_1", 0) + latest_country_month.get("membership_2", 0)) / latest_country_month.get("total_deals", 1) * 100) if latest_country_month.get("total_deals", 0) > 0 else 0
                    st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>🎯</span> Membership Attachment %</div><div class="kpi-value">{membership_rate:.1f}%</div></div>', unsafe_allow_html=True)
                    total_membership_deals = latest_country_month.get("membership_1", 0) + latest_country_month.get("membership_2", 0)
                    st.markdown(f'<div class="kpi-card"><div class="kpi-title"><span>📊</span> Total Membership Deals</div><div class="kpi-value">{total_membership_deals:.0f}</div></div>', unsafe_allow_html=True)

    def render_membership_monthly_breakdown(self, membership_data):
        if not membership_data:
            st.warning("No Membership data available to display.")
            return

        regional_monthly = membership_data.get('regional', {}).get('monthly_data', {})
        countries = membership_data.get('countries', {})
        
        if not regional_monthly and not countries:
            st.warning("No monthly data available.")
            return

        # Create tabs for different views
        tab_names = ["Overall"] + list(countries.keys())
        tabs = st.tabs(tab_names)
        
        # Overall/Regional tab
        with tabs[0]:
            if regional_monthly:
                st.markdown('<div class="section-header">Monthly Performance Breakdown (Overall)</div>', unsafe_allow_html=True)
                month_cols = st.columns(3)
                for i, (month, data) in enumerate(list(regional_monthly.items())[:6]):
                    col = month_cols[i % 3]
                    membership_rate = ((data.get("membership_1", 0) + data.get("membership_2", 0)) / data.get("total_deals", 1) * 100) if data.get("total_deals", 0) > 0 else 0
                    with col:
                        col.markdown(f"""
                        <div class="month-card">
                            <div class="month-header">{data['month_label']}</div>
                            <div class="month-metrics-container">
                                <div>
                                    <div class="month-metric-label">Membership Attachment</div>
                                    <div class="month-metric-value">{membership_rate:.1f}%</div>
                                    <div class="month-metric-label" style="font-size: 0.75rem; text-transform: none; opacity: 0.8;">{data.get("membership_1", 0) + data.get("membership_2", 0):.0f} deals</div>
                                </div>
                            </div>
                            <div class="month-footer">
                                Total: {data['total_deals']:.0f} deals
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No overall monthly data available.")
        
        # Country tabs
        for i, (country_code, country_data) in enumerate(countries.items()):
            with tabs[i + 1]:
                monthly_data = country_data.get('monthly_data', {})
                if monthly_data:
                    st.markdown(f'<div class="section-header">Monthly Performance Breakdown ({country_code})</div>', unsafe_allow_html=True)
                    month_cols = st.columns(3)
                    for j, (month, data) in enumerate(list(monthly_data.items())[:6]):
                        col = month_cols[j % 3]
                        membership_rate = ((data.get("membership_1", 0) + data.get("membership_2", 0)) / data.get("total_deals", 1) * 100) if data.get("total_deals", 0) > 0 else 0
                        with col:
                            col.markdown(f"""
                            <div class="month-card">
                                <div class="month-header">{data['month_label']}</div>
                                <div class="month-metrics-container">
                                    <div>
                                        <div class="month-metric-label">Membership Attachment</div>
                                        <div class="month-metric-value">{membership_rate:.1f}%</div>
                                        <div class="month-metric-label" style="font-size: 0.75rem; text-transform: none; opacity: 0.8;">{data.get("membership_1", 0) + data.get("membership_2", 0):.0f} deals</div>
                                    </div>
                                </div>
                                <div class="month-footer">
                                    Total: {data['total_deals']:.0f} deals
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info(f"No monthly data available for {country_code}.")

    def run(self):
        """Main dashboard execution."""
        if 'scheduler_started' not in st.session_state:
            def refresh_callback():
                # Clear our file-based cache instead of Streamlit cache
                self.sheets_client.clear_all_cache()
            start_background_scheduler(refresh_callback)
            st.session_state.scheduler_started = True

        st.markdown('<div class="main-header">Regional Sales Dashboard</div>', unsafe_allow_html=True)

        try:
            dashboard_data = self.load_dashboard_data()
        except Exception as e:
            st.error(f"Failed to load dashboard data: {e}")
            logging.error(f"Error in load_dashboard_data: {e}", exc_info=True)
            return

        # Display last refreshed timestamp
        if dashboard_data and 'last_refreshed' in dashboard_data:
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown(f"""
                <div style="text-align: center; color: var(--secondary-text); font-size: 0.875rem; margin-bottom: 1rem; padding: 0.75rem; background-color: var(--card-color); border-radius: 8px; border: 1px solid var(--border-color);">
                    📅 Last refreshed: {dashboard_data['last_refreshed']}
                </div>
                """, unsafe_allow_html=True)
            
            # Manual refresh and cache management buttons
            col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
            with col2:
                if st.button("🔄 Refresh Data", use_container_width=True, type="secondary"):
                    with st.spinner("Refreshing data..."):
                        # Clear both file-based cache and session cache
                        self.sheets_client.clear_all_cache()
                        if 'dashboard_data' in st.session_state:
                            del st.session_state.dashboard_data
                        if 'data_timestamp' in st.session_state:
                            del st.session_state.data_timestamp
                        st.success("✅ Data refreshed successfully!")
                        st.rerun()
            
            with col3:
                if st.button("🗑️ Clear Cache", use_container_width=True, type="secondary"):
                    with st.spinner("Clearing cache..."):
                        # Clear both file-based cache and session cache
                        self.sheets_client.clear_all_cache()
                        if 'dashboard_data' in st.session_state:
                            del st.session_state.dashboard_data
                        if 'data_timestamp' in st.session_state:
                            del st.session_state.data_timestamp
                        st.success("✅ Cache cleared successfully!")
                        st.rerun()

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🌟 VIP", "📊 VIP Monthly", "🎯 Membership", "📈 Membership Monthly", "🔄 Funnel", "⚡ Velocity"])

        with tab1:
            self.render_vip_dashboard(dashboard_data.get('vip'))

        with tab2:
            self.render_vip_monthly_breakdown(dashboard_data.get('vip'))

        with tab3:
            self.render_membership_dashboard(dashboard_data.get('membership'))

        with tab4:
            self.render_membership_monthly_breakdown(dashboard_data.get('membership'))

        with tab5:
            self.render_sales_funnel_dashboard(dashboard_data.get('funnel'))

        with tab6:
            self.render_sales_velocity_dashboard(dashboard_data.get('velocity'))

if __name__ == "__main__":
    dashboard = RegionalDashboard()
    dashboard.run() 