"""Ban monitoring service module"""
import asyncio
import logging
import time
import random
from datetime import datetime
from typing import Optional
import discord

logger = logging.getLogger("ig_monitor_bot")

class BanMonitorService:
    """Service for monitoring account bans"""
    
    def __init__(self, instagram_api, ban_data_manager, discord_client, config):
        self.instagram_api = instagram_api
        self.ban_data_manager = ban_data_manager
        self.client = discord_client
        self.config = config
        self.active_monitors = {}  # Track active monitoring tasks
    
    def format_elapsed_time(self, seconds: float) -> str:
        """Format elapsed time in human-readable format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = round(seconds % 60, 1)
        parts = []
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if secs or not parts:
            parts.append(f"{secs}s")
        return ' '.join(parts)
    
    async def monitor_account_for_ban(self, username: str, channel_id: int):
        """Monitor account for ban detection"""
        start_time = time.time()
        channel = self.client.get_channel(channel_id)
        consecutive_errors = 0
        
        logger.info(f"Started ban monitoring for @{username}")
        
        while self.ban_data_manager.is_monitoring(username):
            # Randomized check interval
            check_interval = random.randint(
                self.config.min_check_interval,
                self.config.max_check_interval
            )
            
            status_code, data = await self.instagram_api.fetch_profile(username)
            
            # Check if account is banned (only check on successful fetch)
            if status_code == 200 or status_code == 404:
                is_banned = self._check_if_banned(username, status_code, data)
                
                if is_banned:
                    await self._handle_ban_detected(
                        username,
                        data,
                        channel,
                        start_time,
                        status_code
                    )
                    return
            
            # Handle errors
            elif status_code in [400, 401]:
                consecutive_errors += 1
                logger.warning(f"[@{username}] Consecutive errors: {consecutive_errors}")
                
                if consecutive_errors >= 3:
                    extra_delay = random.randint(300, 600)
                    logger.info(f"[@{username}] Adding {extra_delay}s cooldown")
                    await asyncio.sleep(extra_delay)
                    consecutive_errors = 0
            else:
                consecutive_errors = 0
            
            logger.info(f"[@{username}] Ban check - Next in {check_interval//60} minutes")
            await asyncio.sleep(check_interval)
        
        logger.info(f"Stopped ban monitoring for @{username}")
    
    def _check_if_banned(self, requested_username: str, status_code: int, data: Optional[dict]) -> bool:
        """
        Check if account is banned
        Logic: 
        - Status 404 = BANNED
        - Status 200 + NO user data = BANNED (account exists but no profile = banned)
        - Status 200 + user data + username mismatch = BANNED (username changed)
        - Status 200 + user data + username match = NOT BANNED (keep monitoring)
        """
        requested_lower = requested_username.lower()
        
        # Case 1: 404 = account not found = BANNED
        if status_code == 404:
            logger.warning(f"[@{requested_username}] 🚫 404 status - Account BANNED/DELETED")
            return True
        
        # Case 2: Status 200 - check for user data
        if status_code == 200:
            if not data:
                logger.warning(f"[@{requested_username}] 🚫 200 but no response data - Account BANNED")
                return True
                
            user_data = data.get("data", {}).get("user")
            
            # NO USER DATA = BANNED (Instagram returns 200 but empty user when banned)
            if not user_data:
                logger.warning(f"[@{requested_username}] 🚫 200 but NO user data - Account BANNED")
                return True
            
            # User data exists - compare username
            response_username = user_data.get("username", "").lower()
            
            if not response_username:
                logger.warning(f"[@{requested_username}] 🚫 200 but no username field - Account BANNED")
                return True
            
            logger.info(f"[@{requested_username}] Comparing: '{requested_lower}' vs '{response_username}'")
            
            # Username match = still active
            if response_username == requested_lower:
                logger.info(f"[@{requested_username}] ✅ Username MATCH - Active, continuing monitoring")
                return False
            
            # Username mismatch = banned/changed username
            else:
                logger.warning(f"[@{requested_username}] 🚫 Username MISMATCH - Account BANNED")
                logger.warning(f"[@{requested_username}] Expected: @{requested_lower} | Got: @{response_username}")
                return True
        
        # Any other status = keep monitoring (could be temporary error)
        logger.info(f"[@{requested_username}] Status {status_code} - continuing monitoring")
        return False
    
    async def _handle_ban_detected(
        self,
        username: str,
        data: Optional[dict],
        channel: Optional[discord.TextChannel],
        start_time: float,
        status_code: int
    ):
        """Handle when account ban is detected"""
        elapsed = time.time() - start_time
        elapsed_str = self.format_elapsed_time(elapsed)
        
        # Extract info if available
        followers = following = posts = 0
        actual_username = "Unknown"
        full_name = "N/A"
        
        if data and data.get("data", {}).get("user"):
            user = data["data"]["user"]
            followers = user.get("edge_followed_by", {}).get("count", 0)
            following = user.get("edge_follow", {}).get("count", 0)
            posts = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
            actual_username = user.get("username", "Unknown")
            full_name = user.get("full_name", "N/A")
        
        logger.info(f"[@{username}] 🚫 BAN DETECTED after {elapsed_str}")
        
        if channel:
            try:
                embed = discord.Embed(title="Account Ban Detected", color=0xff0000)
                embed.add_field(name="Username", value=f"@{username}", inline=True)
                embed.add_field(name="Time Taken", value=elapsed_str, inline=True)
                await channel.send(embed=embed)
                
            except Exception as e:
                logger.error(f"Error sending ban notification: {e}")
                # Send simple text message as fallback
                message_text = f"🚫 Account Ban Detected | @{username}\n⏱️ Time Taken: {elapsed_str}"
                await channel.send(content=message_text)
        
        # Remove from monitoring
        self.ban_data_manager.remove_account(username)
        if username in self.active_monitors:
            del self.active_monitors[username]
    
    def start_monitoring(self, username: str, channel_id: int):
        """Start monitoring an account for bans"""
        task = asyncio.create_task(self.monitor_account_for_ban(username, channel_id))
        self.active_monitors[username] = task
        return task
    
    def stop_monitoring(self, username: str):
        """Stop monitoring an account"""
        self.ban_data_manager.remove_account(username)
        if username in self.active_monitors:
            task = self.active_monitors[username]
            task.cancel()
            del self.active_monitors[username]
    
    def stop_all_monitoring(self):
        """Stop monitoring all accounts"""
        for username in list(self.active_monitors.keys()):
            self.stop_monitoring(username)
        self.ban_data_manager.clear_all()
    
    def resume_all_monitoring(self):
        """Resume monitoring for all accounts in database"""
        for username, data in self.ban_data_manager.get_all_accounts().items():
            channel_id = data["channel_id"]
            logger.info(f"Resuming ban monitoring for @{username}")
            self.start_monitoring(username, channel_id)