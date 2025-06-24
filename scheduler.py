import schedule
import time
import threading
from datetime import datetime
import pytz
from config import DASHBOARD_CONFIG
import streamlit as st
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataRefreshScheduler:
    def __init__(self, refresh_callback=None):
        self.refresh_callback = refresh_callback
        self.timezone = pytz.timezone(DASHBOARD_CONFIG['timezone'])
        self.is_running = False
        self.scheduler_thread = None
        
    def refresh_data(self):
        """Callback function to refresh data"""
        try:
            current_time = datetime.now(self.timezone).strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Scheduled data refresh started at {current_time}")
            
            if self.refresh_callback:
                self.refresh_callback()
            
            # Clear Streamlit cache to force refresh
            if hasattr(st, 'cache_data'):
                st.cache_data.clear()
            
            logger.info("Scheduled data refresh completed")
            
        except Exception as e:
            logger.error(f"Error during scheduled refresh: {e}")
    
    def setup_schedule(self):
        """Setup the refresh schedule"""
        schedule.clear()  # Clear any existing schedules
        
        for refresh_time in DASHBOARD_CONFIG['refresh_times']:
            schedule.every().day.at(refresh_time).do(self.refresh_data)
            logger.info(f"Scheduled data refresh at {refresh_time}")
    
    def run_scheduler(self):
        """Run the scheduler in a separate thread"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if not self.is_running:
            self.setup_schedule()
            self.is_running = True
            self.scheduler_thread = threading.Thread(target=self.run_scheduler, daemon=True)
            self.scheduler_thread.start()
            logger.info("Data refresh scheduler started")
    
    def stop_scheduler(self):
        """Stop the background scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        schedule.clear()
        logger.info("Data refresh scheduler stopped")
    
    def get_next_refresh_time(self):
        """Get the next scheduled refresh time"""
        try:
            next_run = schedule.next_run()
            if next_run:
                return next_run.astimezone(self.timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
            return "No upcoming refresh scheduled"
        except Exception:
            return "Unable to determine next refresh time"
    
    def manual_refresh(self):
        """Manually trigger a data refresh"""
        logger.info("Manual data refresh triggered")
        self.refresh_data()

# Global scheduler instance
scheduler_instance = None

def get_scheduler(refresh_callback=None):
    """Get or create the global scheduler instance"""
    global scheduler_instance
    if scheduler_instance is None:
        scheduler_instance = DataRefreshScheduler(refresh_callback)
    return scheduler_instance

def start_background_scheduler(refresh_callback=None):
    """Start the background scheduler"""
    scheduler = get_scheduler(refresh_callback)
    scheduler.start_scheduler()
    return scheduler

def stop_background_scheduler():
    """Stop the background scheduler"""
    global scheduler_instance
    if scheduler_instance:
        scheduler_instance.stop_scheduler()
        scheduler_instance = None 