"""Account monitoring service module"""
import asyncio
import logging
import time
import random
from datetime import datetime
from typing import Optional
import discord
import json

logger = logging.getLogger("ig_monitor_bot")

class MonitorService:
    def __init__(self, instagram_api, data_manager, screenshot_gen, discord_client, config):
        self.instagram_api = instagram_api
        self.data_manager = data_manager
        self.screenshot_gen = screenshot_gen
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
    
    async def monitor_account(self, username: str, channel_id: int):
        """Monitor a single account with randomized check intervals"""
        start_time = time.time()
        channel = self.client.get_channel(channel_id)
        consecutive_errors = 0
        
        logger.info(f"Started monitoring @{username}")
        
        while self.data_manager.is_monitoring(username):
            # Randomized check interval to avoid patterns
            check_interval = random.randint(
                self.config.min_check_interval,
                self.config.max_check_interval
            )
            
            status_code, data = await self.instagram_api.fetch_profile(username)

            # Save response for debugging
            # try:

            #     def _write_debug():
            #         with open("response.json", "w", encoding="utf-8") as f:
            #             json.dump({"status_code": status_code, "data": data}, f, ensure_ascii=False, indent=2)

            #     await asyncio.to_thread(_write_debug)
            # except Exception as e:
            #     logger.error(f"Failed to write debug response.json: {e}")
            
            # Account recovered!
            if data and data.get("data", {}).get("user"):
                await self._handle_account_recovery(
                    username, 
                    data, 
                    channel, 
                    start_time
                )
                return
            
            # Handle errors
            elif status_code in [400, 401]:
                consecutive_errors += 1
                logger.warning(f"[@{username}] Consecutive errors: {consecutive_errors}")
                
                # If getting persistent 400/401, increase wait time dramatically
                if consecutive_errors >= 3:
                    extra_delay = random.randint(20, 40)  # 20-40 seconds extra
                    logger.info(f"[@{username}] Adding {extra_delay}s cooldown due to detection")
                    await asyncio.sleep(extra_delay)
                    consecutive_errors = 0  # Reset counter
            else:
                consecutive_errors = 0  # Reset on any other status
            
            logger.info(f"[@{username}] Next check in {check_interval} seconds")
            await asyncio.sleep(check_interval)
        
        logger.info(f"Stopped monitoring @{username}")
    
    async def _handle_account_recovery(
        self, 
        username: str, 
        data: dict, 
        channel: Optional[discord.TextChannel],
        start_time: float
    ):
        """Handle when an account is recovered"""
        user = data["data"]["user"]
        followers = user.get("edge_followed_by", {}).get("count", 0)
        following = user.get("edge_follow", {}).get("count", 0)
        posts = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
        profile_pic_url = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
        full_name = user.get("full_name", "")
        bio = user.get("biography", "")
        
        elapsed = time.time() - start_time
        elapsed_str = self.format_elapsed_time(elapsed)
        
        message_text = (
            f"Account Recovered | @{username} 🏆✅\n"
            f"Followers: {followers:,} | Following: {following:,}\n"
            f"⏱️ Time Taken: {elapsed_str}"
        )
        
        logger.info(f"[@{username}] Account recovered after {elapsed_str}")
        
        if channel:
            try:
                if self.config.generate_screenshots and profile_pic_url:
                    await self._send_with_screenshot(
                        channel, 
                        username, 
                        profile_pic_url,
                        followers, 
                        following, 
                        posts,
                        full_name, 
                        bio, 
                        message_text
                    )
                else:
                    await channel.send(content=message_text)
            except Exception as e:
                logger.error(f"Error sending recovery message: {e}")
                await channel.send(content=message_text)
        
        # Remove from monitoring
        self.data_manager.remove_account(username)
        if username in self.active_monitors:
            del self.active_monitors[username]
    
    async def _send_with_screenshot(
        self,
        channel: discord.TextChannel,
        username: str,
        profile_pic_url: str,
        followers: int,
        following: int,
        posts: int,
        full_name: str,
        bio: str,
        message_text: str
    ):
        """Send recovery message with screenshot"""
        # Download profile picture
        image_data = await self.instagram_api.download_profile_picture(profile_pic_url)
        
        # Generate screenshot
        screenshot = await asyncio.to_thread(
            self.screenshot_gen.create_screenshot,
            username,
            image_data,
            followers,
            following,
            posts,
            full_name,
            bio
        )
        
        if screenshot:
            file = discord.File(screenshot, filename=f"{username}_profile.png")
            embed = discord.Embed(color=0x2ecc71)
            embed.set_image(url=f"attachment://{username}_profile.png")
            await channel.send(embed=embed, file=file, content=message_text)
        else:
            await channel.send(content=message_text)
    
    def start_monitoring(self, username: str, channel_id: int):
        """Start monitoring an account"""
        task = asyncio.create_task(self.monitor_account(username, channel_id))
        self.active_monitors[username] = task
        return task
    
    def stop_monitoring(self, username: str):
        """Stop monitoring an account"""
        self.data_manager.remove_account(username)
        if username in self.active_monitors:
            task = self.active_monitors[username]
            task.cancel()
            del self.active_monitors[username]
    
    def stop_all_monitoring(self):
        """Stop monitoring all accounts"""
        for username in list(self.active_monitors.keys()):
            self.stop_monitoring(username)
        self.data_manager.clear_all()
    
    def resume_all_monitoring(self):
        """Resume monitoring for all accounts in database"""
        for username, data in self.data_manager.get_all_accounts().items():
            channel_id = data["channel_id"]
            logger.info(f"Resuming monitoring for @{username}")
            self.start_monitoring(username, channel_id)