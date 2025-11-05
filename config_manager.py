"""Configuration management module"""
import json
import os

class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
        self.save_config()
    
    def update(self, **kwargs):
        """Update multiple configuration values"""
        self.config.update(kwargs)
        self.save_config()
    
    @property
    def discord_token(self):
        return self.get("DISCORD_TOKEN", "")
    
    @property
    def admin_user_ids(self):
        return self.get("ADMIN_USER_IDS", [])
    
    @property
    def proxy_username(self):
        return self.get("PROXY_USERNAME", "")
    
    @property
    def proxy_password(self):
        return self.get("PROXY_PASSWORD", "")
    
    @property
    def proxy_gateway(self):
        return self.get("PROXY_GATEWAY", "")
    
    @property
    def generate_screenshots(self):
        return self.get("GENERATE_SCREENSHOTS", True)
    
    @generate_screenshots.setter
    def generate_screenshots(self, value):
        self.set("GENERATE_SCREENSHOTS", value)
    
    @property
    def min_check_interval(self):
        return self.get("MIN_CHECK_INTERVAL", 180)
    
    @min_check_interval.setter
    def min_check_interval(self, value):
        self.set("MIN_CHECK_INTERVAL", value)
    
    @property
    def max_check_interval(self):
        return self.get("MAX_CHECK_INTERVAL", 420)
    
    @max_check_interval.setter
    def max_check_interval(self, value):
        self.set("MAX_CHECK_INTERVAL", value)
    
    def get_proxy_url(self):
        """Get formatted proxy URL"""
        if self.proxy_username and self.proxy_password and self.proxy_gateway:
            return f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_gateway}"
        return None