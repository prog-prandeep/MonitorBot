"""Ban monitoring data management module"""
import json
import os
from datetime import datetime

class BanDataManager:
    """Manages ban monitoring data persistence"""
    
    def __init__(self, ban_file="ban_monitor.json"):
        self.ban_file = ban_file
        self.ban_monitoring = self.load_ban_monitoring()
    
    def load_ban_monitoring(self):
        """Load ban monitoring data from file"""
        if os.path.exists(self.ban_file):
            with open(self.ban_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_ban_monitoring(self):
        """Save ban monitoring data to file"""
        with open(self.ban_file, 'w') as f:
            json.dump(self.ban_monitoring, f, indent=2)
    
    def add_account(self, username, channel_id, user_id):
        """Add account to ban monitoring"""
        self.ban_monitoring[username] = {
            "channel_id": channel_id,
            "started_at": datetime.now().isoformat(),
            "started_by": user_id
        }
        self.save_ban_monitoring()
    
    def remove_account(self, username):
        """Remove account from ban monitoring"""
        if username in self.ban_monitoring:
            del self.ban_monitoring[username]
            self.save_ban_monitoring()
            return True
        return False
    
    def clear_all(self):
        """Clear all ban monitoring accounts"""
        count = len(self.ban_monitoring)
        self.ban_monitoring.clear()
        self.save_ban_monitoring()
        return count
    
    def get_account(self, username):
        """Get ban monitoring data for specific account"""
        return self.ban_monitoring.get(username)
    
    def is_monitoring(self, username):
        """Check if account is being monitored for bans"""
        return username in self.ban_monitoring
    
    def get_all_accounts(self):
        """Get all ban monitored accounts"""
        return self.ban_monitoring.copy()
    
    def get_account_count(self):
        """Get count of ban monitored accounts"""
        return len(self.ban_monitoring)
    
    def get_accounts_by_channel(self, channel_id):
        """Get all accounts monitored in specific channel"""
        return {
            username: data 
            for username, data in self.ban_monitoring.items() 
            if data["channel_id"] == channel_id
        }