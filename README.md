# Regional Sales Dashboard

A comprehensive Streamlit dashboard for tracking regional sales performance across Malaysia, Philippines, and Thailand.

## 🌟 Features

- **VIP Dashboard**: Track VIP deals and conversion rates
- **Membership Dashboard**: Monitor membership attachment rates  
- **Sales Funnel**: Analyze conversion rates through the sales pipeline
- **Sales Velocity**: Track time-based sales metrics
- **Real-time Data**: Connected to Google Sheets for live data updates
- **Multi-country Support**: MY, PH, TH with country-specific metrics
- **Performance Optimized**: File-based caching and rate limiting protection

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/nicholaseng23/Regional-Sales-Dashboard.git
   cd Regional-Sales-Dashboard
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Sheets credentials**
   - Place your Google service account JSON file in the project root
   - Update `config.py` with your sheet IDs and ranges

4. **Run the dashboard**
   ```bash
   streamlit run dashboard.py
   ```

### Streamlit Cloud Deployment

1. **Push to GitHub** (already done)
2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Set main file to `dashboard.py`
   - Add environment variables:
     - `GOOGLE_CREDENTIALS`: Base64 encoded service account JSON
     - `TIMEZONE`: `Asia/Kuala_Lumpur`

## 📊 Dashboard Tabs

### 🌟 VIP Dashboard
- Regional and country-level VIP metrics
- Onsite vs Remote VIP percentages
- Monthly performance breakdown

### 🎯 Membership Dashboard  
- Membership attachment rates by country
- Total membership deals tracking
- Monthly membership trends

### 🔄 Sales Funnel
- Conversion rates through sales pipeline
- Lead to Win percentages
- Country-specific funnel analysis

### ⚡ Sales Velocity
- Time-based sales metrics
- Weekly velocity tracking
- Performance averages

## 🛠️ Technical Stack

- **Frontend**: Streamlit
- **Data Source**: Google Sheets API
- **Caching**: File-based caching system
- **Styling**: Custom CSS with dark theme
- **Performance**: Rate limiting and optimization

## 📁 Project Structure

```
Regional-Sales-Dashboard/
├── dashboard.py              # Main Streamlit application
├── google_sheets_client.py   # Google Sheets API client
├── data_processor.py         # Data processing and aggregation
├── config.py                 # Configuration and settings
├── requirements.txt          # Python dependencies
├── .streamlit/               # Streamlit configuration
│   └── config.toml
├── README.md                 # This file
├── DEPLOYMENT.md             # Deployment guide
├── PERFORMANCE_GUIDE.md      # Performance optimization guide
└── .gitignore               # Git ignore rules
```

## 🔧 Configuration

Update `config.py` with your Google Sheets configuration:

```python
GOOGLE_SHEETS_CONFIG = {
    'credentials_file': 'path/to/your/credentials.json',
    'sheets': {
        'vip_dashboard_my': {
            'id': 'your_sheet_id',
            'worksheet_name': 'MY',
            'category': 'vip'
        },
        # ... other sheets
    }
}
```

## 🚨 Performance Notes

- **Caching**: Data is cached for 1 hour to reduce API calls
- **Rate Limiting**: 2-second delays between requests
- **Error Handling**: Graceful fallback to cached data
- **Manual Refresh**: Users can manually refresh data

## 📈 Performance Metrics

- **Load Time**: 5-15 seconds (cached) / 20-30 seconds (fresh)
- **Cache Hit Rate**: 80%+ after first load
- **API Calls**: 0-10 per load (cached) / 20-30 per load (fresh)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is private and proprietary.

## 🆘 Support

For issues or questions:
1. Check the logs for error messages
2. Verify Google Sheets API access
3. Ensure all dependencies are installed
4. Check the deployment guide for cloud setup

---

**Built with ❤️ for Regional Sales Analytics** 