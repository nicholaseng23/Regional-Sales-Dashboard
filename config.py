import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

# Handle Google credentials for cloud deployment
def get_google_credentials():
    """Get Google credentials from environment variable or file"""
    # Check if credentials are provided as environment variable (for cloud deployment)
    credentials_env = os.getenv('GOOGLE_CREDENTIALS')
    if credentials_env:
        try:
            # Decode base64 credentials
            credentials_json = base64.b64decode(credentials_env).decode('utf-8')
            return json.loads(credentials_json)
        except Exception as e:
            print(f"Error decoding credentials from environment: {e}")
            return None
    
    # Fallback to credentials file (for local development)
    credentials_file = 'credentials.json'
    if os.path.exists(credentials_file):
        return credentials_file
    
    return None

# Get credentials
GOOGLE_CREDENTIALS = get_google_credentials()

# Google Sheets Configuration
GOOGLE_SHEETS_CONFIG = {
    'credentials_file': GOOGLE_CREDENTIALS,  # Google Service Account credentials
    'sheets': {
        # VIP Dashboard Sheets
        'vip_dashboard_my': {
            'id': '1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE',
            'name': 'Malaysia VIP Data',
            'worksheet_name': 'MY',  # Tab name
            'category': 'vip',
            'ranges': {
                'total_deals': 'V2',
                'onsite_vip': 'V28',
                'remote_vip': 'V30'
            }
        },
        'vip_dashboard_ph': {
            'id': '1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE',
            'name': 'Philippines VIP Data',
            'worksheet_name': 'PH',  # Tab name
            'category': 'vip',
            'ranges': {
                'total_deals': 'V2',
                'onsite_vip': 'V28',
                'remote_vip': 'V30'
            }
        },
        'vip_dashboard_th': {
            'id': '1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE',
            'name': 'Thailand VIP Data',
            'worksheet_name': 'TH',  # Tab name
            'category': 'vip',
            'ranges': {
                'total_deals': 'V2',
                'onsite_vip': 'V28',
                'remote_vip': 'V30'
            }
        },
        # Sales Velocity Sheet (Malaysia only for now) - Weekly data structure
        'sales_velocity_my': {
            'id': '1_KWf7wxtDUyypGsWXzsmCXhLOG8fmN0EapDXoKu_3EE',
            'name': 'Malaysia Sales Velocity',
            'worksheet_name': None,  # Use default sheet
            'category': 'velocity',
            'ranges': {
                # These will be handled by the weekly data parser
                # The actual data structure will be weekly ranges starting from 28/04/2025
                'weekly_data': 'A:Z'  # Full range for weekly parsing
            }
        },
        # Sales Funnel Sheets
        'sales_funnel_my': {
            'id': '1BqnXG90M1yeiznB5B2JN6ZWDC7kdlObBidCpSJGHd6M',  # Sales Funnel sheet
            'name': 'Malaysia Sales Funnel',
            'worksheet_name': 'MY (IB)',
            'category': 'funnel',
            'ranges': {
                # Latest 3 data points: BE54:BS63, BE74:BS83, BE94:BS103
                # Using the latest data point (BE94:BS103) for now
                'leads': 'BE94',
                'qualified_leads': 'BE95',
                'opportunities': 'BE96',
                'proposals': 'BE97',
                'negotiations': 'BE98',
                'closed_won': 'BE99',
                'closed_lost': 'BE100'
            }
        },
        'sales_funnel_ph': {
            'id': '1BqnXG90M1yeiznB5B2JN6ZWDC7kdlObBidCpSJGHd6M',  # Sales Funnel sheet
            'name': 'Philippines Sales Funnel',
            'worksheet_name': 'PH (IB)',
            'category': 'funnel',
            'ranges': {
                # All data in BD53:BT84, headers on row 54
                # Using the latest data point from the range
                'leads': 'BD84',
                'qualified_leads': 'BE84',
                'opportunities': 'BF84',
                'proposals': 'BG84',
                'negotiations': 'BH84',
                'closed_won': 'BI84',
                'closed_lost': 'BJ84'
            }
        },
        'sales_funnel_th': {
            'id': '1BqnXG90M1yeiznB5B2JN6ZWDC7kdlObBidCpSJGHd6M',  # Sales Funnel sheet
            'name': 'Thailand Sales Funnel',
            'worksheet_name': 'TH (IB)',
            'category': 'funnel',
            'ranges': {
                # All data in BH47:BV78
                # Using the latest data point from the range
                'leads': 'BH78',
                'qualified_leads': 'BI78',
                'opportunities': 'BJ78',
                'proposals': 'BK78',
                'negotiations': 'BL78',
                'closed_won': 'BM78',
                'closed_lost': 'BN78'
            }
        },
        # Membership Dashboard Sheets
        'membership_dashboard_my': {
            'id': '1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE',
            'name': 'Malaysia Membership Data',
            'worksheet_name': 'MY',  # Tab name
            'category': 'membership',
            'ranges': {
                'total_deals': 'V2',
                'membership_1': 'V43',
                'membership_2': 'V44'
            }
        },
        'membership_dashboard_ph': {
            'id': '1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE',
            'name': 'Philippines Membership Data',
            'worksheet_name': 'PH',  # Tab name
            'category': 'membership',
            'ranges': {
                'total_deals': 'V2',
                'membership_1': 'V43',
                'membership_2': 'V44'
            }
        },
        'membership_dashboard_th': {
            'id': '1CuaZL9s2gLtiolXW419nAMqCXN_fGv2Refp9D8lCzRE',
            'name': 'Thailand Membership Data',
            'worksheet_name': 'TH',  # Tab name
            'category': 'membership',
            'ranges': {
                'total_deals': 'V2',
                'membership_1': 'V30',
                'membership_2': 'V31'
            }
        }
    }
}

# Dashboard Configuration
DASHBOARD_CONFIG = {
    'refresh_times': ['10:00', '16:00'],  # 10 AM and 4 PM
    'timezone': os.getenv('TIMEZONE', 'Asia/Kuala_Lumpur'),  # Use environment variable or default
    'cache_duration': 14400  # Cache data for 4 hours (increased from 1 hour)
}

# Metrics Configuration
METRICS_CONFIG = {
    # VIP Metrics
    'onsite_vip_percentage': {
        'formula': 'onsite_vip / total_deals * 100',
        'format': '{:.1f}%',
        'description': 'Onsite VIP %',
        'category': 'vip'
    },
    'remote_vip_percentage': {
        'formula': 'remote_vip / total_deals * 100',
        'format': '{:.1f}%',
        'description': 'Remote VIP %',
        'category': 'vip'
    },
    'total_vip_percentage': {
        'formula': '(onsite_vip + remote_vip) / total_deals * 100',
        'format': '{:.1f}%',
        'description': 'Total VIP %',
        'category': 'vip'
    },
    'total_deals': {
        'formula': 'total_deals',
        'format': '{:.0f}',
        'description': 'Total Deals',
        'category': 'vip'
    },
    # Sales Funnel Metrics
    'lead_conversion_rate': {
        'formula': 'qualified_leads / leads * 100',
        'format': '{:.1f}%',
        'description': 'Lead Conversion %',
        'category': 'funnel'
    },
    'opportunity_conversion_rate': {
        'formula': 'opportunities / qualified_leads * 100',
        'format': '{:.1f}%',
        'description': 'Opportunity Conversion %',
        'category': 'funnel'
    },
    'close_rate': {
        'formula': 'closed_won / opportunities * 100',
        'format': '{:.1f}%',
        'description': 'Close Rate %',
        'category': 'funnel'
    },
    'total_leads': {
        'formula': 'leads',
        'format': '{:.0f}',
        'description': 'Total Leads',
        'category': 'funnel'
    },
    # Sales Velocity Metrics - Updated for weekly structure
    'lead_to_sql_avg': {
        'formula': 'lead_to_sql_avg',
        'format': '{:.1f} days',
        'description': 'Lead to SQL (Avg)',
        'category': 'velocity'
    },
    'lead_to_ms_avg': {
        'formula': 'lead_to_ms_avg',
        'format': '{:.1f} days',
        'description': 'Lead to MS (Avg)',
        'category': 'velocity'
    },
    'ms_to_1st_meeting_avg': {
        'formula': 'ms_to_1st_meeting_avg',
        'format': '{:.1f} days',
        'description': 'MS to 1st Meeting (Avg)',
        'category': 'velocity'
    },
    'ms_to_mc_avg': {
        'formula': 'ms_to_mc_avg',
        'format': '{:.1f} days',
        'description': 'MS to MC (Avg)',
        'category': 'velocity'
    },
    'mc_to_closed_avg': {
        'formula': 'mc_to_closed_avg',
        'format': '{:.1f} days',
        'description': 'MC to Closed (Avg)',
        'category': 'velocity'
    },
    'lead_to_win_avg': {
        'formula': 'lead_to_win_avg',
        'format': '{:.1f} days',
        'description': 'Lead to Win (Avg)',
        'category': 'velocity'
    },
    # Membership Metrics
    'membership_attachment_rate': {
        'formula': '(membership_1 + membership_2) / total_deals * 100',
        'format': '{:.1f}%',
        'description': 'Membership Attachment Rate %',
        'category': 'membership'
    },
    'total_deals_membership': {
        'formula': 'total_deals',
        'format': '{:.0f}',
        'description': 'Total Deals',
        'category': 'membership'
    }
} 