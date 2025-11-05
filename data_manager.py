"""Data persistence management module"""
import json
import os
from datetime import datetime

class DataManager:
    def __init__(self, monitoring_file="monitoring.json"):
        self.monitoring_file = monitoring_file
        self.monitoring = self.load_monitoring()
    
    def load_monitoring(self):
        """Load monitoring data from file"""
        if os.path.exists(self.monitoring_file):
            with open(self.monitoring_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_monitoring(self):
        """Save monitoring data to file"""
        with open(self.monitoring_file, 'w') as f:
            json.dump(self.monitoring, f, indent=2)
    
    def add_account(self, username, channel_id, user_id):
        """Add account to monitoring"""
        self.monitoring[username] = {
            "channel_id": channel_id,
            "started_at": datetime.now().isoformat(),
            "started_by": user_id
        }
        self.save_monitoring()
    
    def remove_account(self, username):
        """Remove account from monitoring"""
        if username in self.monitoring:
            del self.monitoring[username]
            self.save_monitoring()
            return True
        return False
    
    def clear_all(self):
        """Clear all monitoring accounts"""
        count = len(self.monitoring)
        self.monitoring.clear()
        self.save_monitoring()
        return count
    
    def get_account(self, username):
        """Get monitoring data for specific account"""
        return self.monitoring.get(username)
    
    def is_monitoring(self, username):
        """Check if account is being monitored"""
        return username in self.monitoring
    
    def get_all_accounts(self):
        """Get all monitored accounts"""
        return self.monitoring.copy()
    
    def get_account_count(self):
        """Get count of monitored accounts"""
        return len(self.monitoring)
    
    def get_accounts_by_channel(self, channel_id):
        """Get all accounts monitored in specific channel"""
        return {
            username: data 
            for username, data in self.monitoring.items() 
            if data["channel_id"] == channel_id
        }