# Regional Sales Dashboard

A comprehensive Streamlit dashboard for tracking regional sales performance across Malaysia, Philippines, and Thailand.

## Features

- **VIP Dashboard**: Track VIP deals and conversion rates
- **Membership Dashboard**: Monitor membership attachment rates
- **Sales Funnel**: Analyze conversion rates through the sales pipeline
- **Sales Velocity**: Track time-based sales metrics
- **Real-time Data**: Connected to Google Sheets for live data updates
- **Multi-country Support**: MY, PH, TH with country-specific metrics

## Deployment

### Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up Google Sheets credentials (see Configuration section)
4. Run: `streamlit run dashboard.py`

### Streamlit Cloud Deployment

1. Push your code to GitHub
2. Connect your GitHub repository to Streamlit Cloud
3. Set up environment variables (see Configuration section)
4. Deploy!

## Configuration

### Google Sheets Setup

1. Create a Google Cloud Project
2. Enable Google Sheets API
3. Create a service account and download credentials
4. Share your Google Sheets with the service account email

### Environment Variables

Set these in Streamlit Cloud:
- `GOOGLE_CREDENTIALS`: Your service account JSON (base64 encoded)
- `TIMEZONE`: Your timezone (e.g., "Asia/Kuala_Lumpur")

## File Structure

```
├── dashboard.py              # Main dashboard application
├── google_sheets_client.py   # Google Sheets API client
├── data_processor.py         # Data processing logic
├── config.py                 # Configuration settings
├── scheduler.py              # Background data refresh
├── requirements.txt          # Python dependencies
└── .streamlit/              # Streamlit configuration
    └── config.toml
```

## Access Control

**Important**: By default, Streamlit Cloud deployments are public. Anyone with the link can access your dashboard.

### To restrict access:

1. **Streamlit Cloud Pro**: Upgrade to Pro for authentication features
2. **Custom Domain**: Use a custom domain with authentication
3. **VPN/Network Restrictions**: Deploy behind a VPN or corporate network

## Rate Limiting

The dashboard includes built-in rate limiting for Google Sheets API:
- Automatic retry with exponential backoff
- Request delays between API calls
- Fallback to cached data when rate limited

## Support

For issues or questions, please check the logs in Streamlit Cloud or contact the development team.

## Key Metrics Tracked

1. **Leads to Meeting Scheduled %**: Conversion rate from leads to scheduled meetings
2. **Meeting to Opportunity %**: Conversion rate from meetings to opportunities
3. **Opportunity to Close %**: Conversion rate from opportunities to closed deals
4. **Total Revenue**: Sum of all revenue across regions

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Sheets Setup

#### A. Create a Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API and Google Drive API
4. Create a Service Account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Fill in the details and create
5. Generate a key:
   - Click on your service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create New Key"
   - Choose JSON format
   - Download the file and rename it to `credentials.json`
   - Place it in your project root directory

#### B. Share Your Google Sheets

1. Open each of your 3 Google Sheets
2. Click "Share" button
3. Add the service account email (found in credentials.json) with "Editor" permissions
4. Copy the Sheet ID from the URL (the long string between `/d/` and `/edit`)

### 3. Configuration

#### A. Environment Variables
1. Copy `.env.example` to `.env`
2. Fill in your Google Sheets IDs:

```env
SHEET_A_ID=your_malaysia_sheet_id_here
SHEET_B_ID=your_philippines_sheet_id_here  
SHEET_C_ID=your_thailand_sheet_id_here
```

#### B. Configure Data Ranges
Edit `config.py` to specify which cells contain your data:

```python
'ranges': {
    'total_leads': 'B2',        # Cell containing total leads count
    'meetings_scheduled': 'C2',  # Cell containing meetings scheduled count
    'opportunities': 'D2',       # Cell containing opportunities count
    'closed_deals': 'E2',       # Cell containing closed deals count
    'revenue': 'F2'             # Cell containing revenue amount
}
```

### 4. Run the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will be available at `http://localhost:8501`

## Dashboard Structure

```
Regional%20Sales%20Dashboard%20V2/
├── dashboard.py              # Main Streamlit application
├── google_sheets_client.py   # Google Sheets integration
├── data_processor.py         # Data processing and calculations
├── scheduler.py              # Auto-refresh scheduling
├── config.py                # Configuration settings
├── requirements.txt          # Python dependencies
├── credentials.json          # Google Service Account credentials (you create this)
├── .env                     # Environment variables (you create this)
├── .env.example             # Example environment file
└── README.md               # This file
```

## Customization

### Adding New Metrics

1. Edit `config.py` and add your metric to `METRICS_CONFIG`:

```python
'your_new_metric': {
    'formula': 'your_formula_here',  # e.g., 'closed_deals / total_leads * 100'
    'format': '{:.1f}%',             # How to display the result
    'description': 'Your metric description'
}
```

### Changing Refresh Times

Edit `config.py` to modify refresh schedule:

```python
DASHBOARD_CONFIG = {
    'refresh_times': ['09:00', '15:00'],  # 9 AM and 3 PM
    'timezone': 'Asia/Singapore',         # Your timezone
}
```

### Adding More Countries/Sheets

Add new sheets to `config.py`:

```python
'sheet_d': {
    'id': os.getenv('SHEET_D_ID', ''),
    'name': 'Vietnam Data',
    'ranges': {
        'total_leads': 'B2',
        # ... other ranges
    }
}
```

## Troubleshooting

### Common Issues

1. **"Failed to connect to Google Sheets"**
   - Check that `credentials.json` is in the project root
   - Verify the service account email has access to your sheets
   - Ensure Google Sheets API is enabled in Google Cloud Console

2. **"No sheet ID configured"**
   - Check your `.env` file has the correct Sheet IDs
   - Verify the Sheet IDs are correct (found in the Google Sheets URL)

3. **"Connection failed"**
   - Verify your internet connection
   - Check that the Google Sheets are not private/restricted

4. **Metrics showing as 0**
   - Check that the cell ranges in `config.py` match your sheet structure
   - Verify the cells contain numeric values, not text

### Debug Mode

The dashboard includes a "Raw Data (Debug)" section that shows the actual data being pulled from your sheets. Use this to verify your configuration is correct.

## Security Notes

- Never commit `credentials.json` or `.env` files to version control
- Keep your service account credentials secure
- Regularly rotate your service account keys
- Use minimal permissions (Editor access only to specific sheets)

## Auto-Refresh Schedule

The dashboard automatically refreshes data:
- **10:00 AM** - Morning update
- **4:00 PM** - Afternoon update

You can also manually refresh using the "Manual Refresh" button in the sidebar. 