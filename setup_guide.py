#!/usr/bin/env python3
"""
Interactive setup guide for Regional Sales Dashboard
"""

import os
import json
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🌏 Regional Sales Dashboard Setup Guide")
    print("=" * 60)
    print()

def check_credentials():
    """Check if credentials.json exists"""
    if Path("credentials.json").exists():
        print("✅ credentials.json found")
        return True
    else:
        print("❌ credentials.json not found")
        print("\n📋 To create credentials.json:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Google Sheets API and Google Drive API")
        print("4. Create a Service Account")
        print("5. Generate a JSON key and save as 'credentials.json'")
        print("6. Share your Google Sheets with the service account email")
        return False

def setup_env_file():
    """Setup .env file with Google Sheets IDs"""
    print("\n📝 Setting up environment variables...")
    
    if Path(".env").exists():
        print("⚠️  .env file already exists")
        overwrite = input("Do you want to overwrite it? (y/N): ").lower()
        if overwrite != 'y':
            return
    
    print("\nPlease provide your Google Sheets IDs:")
    print("(You can find the Sheet ID in the URL: https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit)")
    
    sheet_a_id = input("\n🇲🇾 Malaysia Sheet ID: ").strip()
    sheet_b_id = input("🇵🇭 Philippines Sheet ID: ").strip()
    sheet_c_id = input("🇹🇭 Thailand Sheet ID: ").strip()
    
    env_content = f"""# Google Sheets Configuration
SHEET_A_ID={sheet_a_id}
SHEET_B_ID={sheet_b_id}
SHEET_C_ID={sheet_c_id}
"""
    
    with open(".env", "w") as f:
        f.write(env_content)
    
    print("✅ .env file created successfully!")

def check_dependencies():
    """Check if required packages are installed"""
    print("\n📦 Checking dependencies...")
    
    required_packages = [
        'streamlit', 'gspread', 'google-auth', 'pandas', 
        'numpy', 'plotly', 'python-dotenv', 'schedule', 'pytz'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package}")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    else:
        print("\n✅ All dependencies installed!")
        return True

def configure_data_ranges():
    """Guide user through configuring data ranges"""
    print("\n📊 Data Range Configuration")
    print("Edit config.py to specify which cells contain your data.")
    print("\nCurrent configuration:")
    print("- total_leads: B2")
    print("- meetings_scheduled: C2") 
    print("- opportunities: D2")
    print("- closed_deals: E2")
    print("- revenue: F2")
    
    print("\nMake sure these cell references match your Google Sheets structure.")
    
    modify = input("\nDo you want to modify these ranges now? (y/N): ").lower()
    if modify == 'y':
        print("\nPlease edit the 'ranges' section in config.py manually.")
        print("Example structure:")
        print("""
'ranges': {
    'total_leads': 'B2',        # Your leads count cell
    'meetings_scheduled': 'C2',  # Your meetings count cell
    'opportunities': 'D2',       # Your opportunities count cell
    'closed_deals': 'E2',       # Your closed deals count cell
    'revenue': 'F2'             # Your revenue cell
}
""")

def test_setup():
    """Test the setup"""
    print("\n🧪 Testing setup...")
    
    try:
        from google_sheets_client import GoogleSheetsClient
        client = GoogleSheetsClient()
        
        is_connected, message = client.test_connection()
        
        if is_connected:
            print("✅ Google Sheets connection successful!")
            return True
        else:
            print(f"❌ Connection failed: {message}")
            return False
            
    except Exception as e:
        print(f"❌ Setup test failed: {e}")
        return False

def main():
    print_header()
    
    # Check credentials
    has_credentials = check_credentials()
    
    # Setup environment file
    setup_env_file()
    
    # Check dependencies
    has_dependencies = check_dependencies()
    
    # Configure data ranges
    configure_data_ranges()
    
    # Test setup if all components are ready
    if has_credentials and has_dependencies:
        test_setup()
        
        print("\n🚀 Setup complete!")
        print("\nTo run the dashboard:")
        print("streamlit run dashboard.py")
        print("\nThe dashboard will be available at: http://localhost:8501")
    else:
        print("\n⚠️  Setup incomplete. Please address the issues above.")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main() 