# Render Deployment Instructions

## 🚀 Deploy Regional Sales Dashboard to Render

### Prerequisites
- GitHub repository with your code
- Google Sheets API credentials (JSON file)
- Render account (free)

### Step 1: Prepare Your Repository

1. **Push all files to GitHub** including:
   - `render.yaml` (deployment configuration)
   - `requirements.txt` (dependencies)
   - `.streamlit/config.toml` (Streamlit configuration)
   - All your Python files

2. **Do NOT commit your `credentials.json`** file (it should be in `.gitignore`)

### Step 2: Create Render Service

1. **Go to [render.com](https://render.com)** and sign up/login
2. **Click "New +"** → **"Web Service"**
3. **Connect your GitHub repository**
4. **Choose your repository** containing the dashboard code

### Step 3: Configure Deployment Settings

Render should auto-detect the `render.yaml` file, but verify these settings:

- **Name**: `regional-sales-dashboard`
- **Runtime**: `Python`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `streamlit run dashboard.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true --server.enableCORS=false --server.enableXsrfProtection=false`

### Step 4: Set Environment Variables

**CRITICAL**: You need to add your Google Sheets credentials as environment variables:

1. **In Render Dashboard** → **Your Service** → **Environment**
2. **Add Environment Variable**:
   - **Key**: `GOOGLE_SHEETS_CREDENTIALS`
   - **Value**: Copy the ENTIRE contents of your `credentials.json` file
   - **Important**: Paste the complete JSON as a single line

Example format:
```json
{"type":"service_account","project_id":"your-project","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...","client_id":"...","auth_uri":"...","token_uri":"...","auth_provider_x509_cert_url":"...","client_x509_cert_url":"..."}
```

### Step 5: Deploy

1. **Click "Deploy"** - Render will:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start your Streamlit app
   - Assign a public URL

2. **Monitor the build logs** for any errors

### Step 6: Verify Deployment

1. **Visit your app URL** (provided by Render)
2. **Check that all data loads correctly**
3. **Test VIP, Membership, Funnel, and Velocity dashboards**

## 🔧 Troubleshooting

### Common Issues:

1. **"Invalid JWT Signature" Error**:
   - Verify your `GOOGLE_SHEETS_CREDENTIALS` environment variable
   - Ensure the JSON is properly formatted (no extra spaces/newlines)

2. **App Won't Start**:
   - Check build logs for dependency issues
   - Verify `requirements.txt` is complete

3. **Data Not Loading**:
   - Check Google Sheets API credentials
   - Verify sheet IDs in `config.py` are correct

4. **App Sleeps After 15 Minutes**:
   - This is normal on Render's free tier
   - First visit after sleep will take 30-50 seconds to wake up
   - Consider upgrading to paid tier ($7/month) for always-on hosting

## 📊 Expected Performance

- **Cold Start**: 30-50 seconds (after sleep)
- **Warm Load**: 2-3 seconds
- **Data Refresh**: 1-2 seconds (with batch optimization)
- **API Calls**: ~12 calls total (vs ~42 without optimization)

## 🔄 Auto-Deploy Setup

1. **Enable Auto-Deploy** in Render dashboard
2. **Every GitHub push** to main branch will trigger automatic deployment
3. **Build time**: ~2-3 minutes

## 💰 Cost Breakdown

- **Free Tier**: 750 hours/month (sufficient for 24/7)
- **Limitations**: Apps sleep after 15 minutes of inactivity
- **Upgrade**: $7/month for always-on hosting

Your dashboard will be live at: `https://regional-sales-dashboard-[random].onrender.com` 