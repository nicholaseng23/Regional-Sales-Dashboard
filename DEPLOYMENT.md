# Streamlit Cloud Deployment Guide

This guide will walk you through deploying your Regional Sales Dashboard to Streamlit Cloud.

## Prerequisites

1. **GitHub Account**: You'll need a GitHub account to host your code
2. **Streamlit Cloud Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)
3. **Google Cloud Project**: For Google Sheets API access

## Step 1: Prepare Your Code

### 1.1 Push to GitHub

1. Create a new GitHub repository
2. Push your dashboard code to the repository:

```bash
git init
git add .
git commit -m "Initial commit: Regional Sales Dashboard"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 1.2 Verify Required Files

Ensure these files are in your repository:
- `dashboard.py` (main application)
- `requirements.txt` (dependencies)
- `.streamlit/config.toml` (Streamlit configuration)
- `config.py` (dashboard configuration)
- `google_sheets_client.py` (Google Sheets client)
- `data_processor.py` (data processing)
- `scheduler.py` (background tasks)

## Step 2: Google Cloud Setup

### 2.1 Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

### 2.2 Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details:
   - Name: `streamlit-dashboard`
   - Description: `Service account for Streamlit dashboard`
4. Click "Create and Continue"
5. Skip role assignment (click "Continue")
6. Click "Done"

### 2.3 Generate Service Account Key

1. Click on your service account
2. Go to "Keys" tab
3. Click "Add Key" > "Create New Key"
4. Choose "JSON" format
5. Download the JSON file

### 2.4 Share Google Sheets

1. Open your Google Sheets
2. Click "Share" button
3. Add your service account email (found in the JSON file)
4. Give "Editor" access
5. Click "Send"

## Step 3: Prepare Credentials for Streamlit Cloud

### 3.1 Convert Credentials to Base64

```bash
# On macOS/Linux
base64 -i your-service-account-key.json

# On Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("your-service-account-key.json"))
```

### 3.2 Copy the Base64 String

Copy the entire base64 output - you'll need this for the next step.

## Step 4: Deploy to Streamlit Cloud

### 4.1 Connect GitHub Repository

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set the main file path: `dashboard.py`
6. Click "Deploy!"

### 4.2 Configure Environment Variables

1. In your app settings, go to "Secrets"
2. Add these secrets:

```toml
GOOGLE_CREDENTIALS = "YOUR_BASE64_ENCODED_CREDENTIALS"
TIMEZONE = "Asia/Kuala_Lumpur"
```

Replace `YOUR_BASE64_ENCODED_CREDENTIALS` with the base64 string from Step 3.1.

### 4.3 Deploy

1. Click "Save" to save the secrets
2. Your app will automatically redeploy
3. Wait for deployment to complete

## Step 5: Verify Deployment

### 5.1 Check App Status

1. Your app URL will be: `https://YOUR_APP_NAME-YOUR_USERNAME.streamlit.app`
2. Check that the dashboard loads without errors
3. Verify that data is being fetched from Google Sheets

### 5.2 Test Features

1. Navigate through all tabs (VIP, Membership, Funnel, Velocity)
2. Check that the timestamp shows correctly
3. Test the manual refresh button
4. Verify country flags and headers display correctly

## Step 6: Access Control (Important!)

### 6.1 Public Access

**By default, your Streamlit Cloud app is PUBLIC.** Anyone with the link can access your dashboard and view your data.

### 6.2 Restrict Access (Optional)

#### Option A: Streamlit Cloud Pro
- Upgrade to Streamlit Cloud Pro ($10/month)
- Enable authentication features
- Control who can access your app

#### Option B: Custom Domain
- Use a custom domain with authentication
- Deploy behind a corporate firewall

#### Option C: Network Restrictions
- Deploy on a private server
- Use VPN or network-level access control

## Troubleshooting

### Common Issues

1. **"Failed to connect to Google Sheets"**
   - Check that your service account has access to the sheets
   - Verify the base64 credentials are correct
   - Ensure Google Sheets API is enabled

2. **"Rate limit exceeded"**
   - The dashboard includes built-in rate limiting
   - Wait a few minutes and try again
   - Consider upgrading Google Cloud quota

3. **"Module not found"**
   - Check that all dependencies are in `requirements.txt`
   - Verify file paths are correct

4. **"Caching errors"**
   - The dashboard has been updated to handle caching issues
   - Try refreshing the page

### Getting Help

1. Check the Streamlit Cloud logs in your app settings
2. Review the console output for error messages
3. Test locally first to isolate issues
4. Contact support if needed

## Security Best Practices

1. **Rotate Credentials**: Regularly update your service account keys
2. **Minimal Permissions**: Only give your service account access to specific sheets
3. **Monitor Usage**: Check Google Cloud Console for API usage
4. **Secure Sharing**: Be careful who you share the dashboard link with

## Cost Considerations

- **Streamlit Cloud**: Free tier available, Pro for $10/month
- **Google Cloud**: Free tier includes 1,000 API calls/day
- **Data Transfer**: Minimal costs for typical usage

## Next Steps

After successful deployment:

1. **Monitor Performance**: Check app performance and API usage
2. **Set Up Alerts**: Configure monitoring for API rate limits
3. **User Training**: Train users on how to use the dashboard
4. **Regular Updates**: Keep dependencies and code updated

Your dashboard is now live and accessible to anyone with the link! 🎉 