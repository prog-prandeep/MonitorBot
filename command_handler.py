"""Discord command handler module with ban monitoring and session management"""
import discord
import asyncio
import random
import time
import logging
from datetime import datetime
from utils import parse_usernames, format_elapsed_time, is_admin, truncate_text

logger = logging.getLogger("ig_monitor_bot")

class CommandHandler:
    def __init__(self, monitor_service, ban_monitor_service, data_manager, ban_data_manager, 
                 instagram_api, session_manager, config, max_monitor=15):
        self.monitor_service = monitor_service
        self.ban_monitor_service = ban_monitor_service
        self.data_manager = data_manager
        self.ban_data_manager = ban_data_manager
        self.instagram_api = instagram_api
        self.session_manager = session_manager
        self.config = config
        self.max_monitor = max_monitor
    
    # ===== UNBAN MONITORING COMMANDS =====
    
    async def handle_unban(self, message: discord.Message, args: str):
        """Handle !unban command"""
        if not args:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!unban username` or `!unban username1 username2`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        usernames = parse_usernames(args)
        
        if not usernames:
            embed = discord.Embed(
                title="❌ No Valid Usernames",
                description="Please provide at least one valid username.",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        already_monitoring = [u for u in usernames if self.data_manager.is_monitoring(u)]
        new_usernames = [u for u in usernames if u not in already_monitoring]
        
        # Check monitor limit
        if self.data_manager.get_account_count() + len(new_usernames) > self.max_monitor:
            remaining_slots = self.max_monitor - self.data_manager.get_account_count()
            embed = discord.Embed(
                title="❌ Monitor Limit Reached",
                description=f"Monitor limit: **{self.max_monitor}**. Currently: **{self.data_manager.get_account_count()}**. Available slots: **{remaining_slots}**",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        # Single username
        if len(new_usernames) == 1:
            await self._handle_single_unban(message, new_usernames[0])
        # Multiple usernames
        else:
            await self._handle_batch_unban(message, new_usernames, already_monitoring)
    
    async def _handle_single_unban(self, message: discord.Message, username: str):
        """Handle single username unban"""
        status_code, _ = await self.instagram_api.fetch_profile(username)
        
        if status_code is None:
            embed = discord.Embed(
                title="🚫 Fetch Failed",
                description=f"Could not fetch **@{username}**. Check proxy/session configuration.",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        self.data_manager.add_account(username, message.channel.id, message.author.id)
        
        embed = discord.Embed(
            title="✅ Unban Monitoring Started",
            description=f"🔍 Now monitoring **@{username}**. You'll be notified when recovered.",
            color=0x3498db
        )
        await message.channel.send(embed=embed)
        self.monitor_service.start_monitoring(username, message.channel.id)
    
    async def _handle_batch_unban(self, message: discord.Message, new_usernames: list, already_monitoring: list):
        """Handle batch username unban"""
        processing_msg = await message.channel.send(embed=discord.Embed(
            title="🔍 Processing Batch...",
            description=f"Adding {len(new_usernames)} accounts...",
            color=0xf1c40f
        ))
        
        success_count = 0
        failed_usernames = []
        
        for username in new_usernames:
            try:
                await asyncio.sleep(random.uniform(3, 6))
                status_code, _ = await self.instagram_api.fetch_profile(username)
                
                if status_code is not None:
                    self.data_manager.add_account(username, message.channel.id, message.author.id)
                    success_count += 1
                    self.monitor_service.start_monitoring(username, message.channel.id)
                else:
                    failed_usernames.append(username)
            except Exception as e:
                logger.error(f"Error processing @{username}: {e}")
                failed_usernames.append(username)
        
        result_parts = []
        if success_count > 0:
            result_parts.append(f"✅ **{success_count}** accounts added")
        if already_monitoring:
            result_parts.append(f"⚠️ **{len(already_monitoring)}** already monitored")
        if failed_usernames:
            result_parts.append(f"❌ **{len(failed_usernames)}** failed")
        
        embed = discord.Embed(
            title="🔍 Batch Results",
            description="\n".join(result_parts),
            color=0x2ecc71 if success_count > 0 else 0xe74c3c
        )
        await processing_msg.edit(embed=embed)
    
    # ===== BAN MONITORING COMMANDS =====
    
    async def handle_ban(self, message: discord.Message, args: str):
        """Handle !ban command"""
        if not args:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!ban username` or `!ban username1 username2`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        usernames = parse_usernames(args)
        
        if not usernames:
            embed = discord.Embed(
                title="❌ No Valid Usernames",
                description="Please provide at least one valid username.",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        already_monitoring = [u for u in usernames if self.ban_data_manager.is_monitoring(u)]
        new_usernames = [u for u in usernames if u not in already_monitoring]
        
        # Check monitor limit
        if self.ban_data_manager.get_account_count() + len(new_usernames) > self.max_monitor:
            remaining_slots = self.max_monitor - self.ban_data_manager.get_account_count()
            embed = discord.Embed(
                title="❌ Monitor Limit Reached",
                description=f"Ban monitor limit: **{self.max_monitor}**. Currently: **{self.ban_data_manager.get_account_count()}**. Available slots: **{remaining_slots}**",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        # Single username
        if len(new_usernames) == 1:
            await self._handle_single_ban(message, new_usernames[0])
        # Multiple usernames
        else:
            await self._handle_batch_ban(message, new_usernames, already_monitoring)
    
    async def _handle_single_ban(self, message: discord.Message, username: str):
        """Handle single username ban monitoring"""
        status_code, _ = await self.instagram_api.fetch_profile(username)
        
        if status_code is None:
            embed = discord.Embed(
                title="🚫 Fetch Failed",
                description=f"Could not fetch **@{username}**. Check proxy/session configuration.",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        self.ban_data_manager.add_account(username, message.channel.id, message.author.id)
        
        embed = discord.Embed(
            title="✅ Ban Monitoring Started",
            description=f"🔍 Now monitoring **@{username}** for bans. You'll be notified when banned.",
            color=0xe67e22
        )
        await message.channel.send(embed=embed)
        self.ban_monitor_service.start_monitoring(username, message.channel.id)
    
    async def _handle_batch_ban(self, message: discord.Message, new_usernames: list, already_monitoring: list):
        """Handle batch ban monitoring"""
        processing_msg = await message.channel.send(embed=discord.Embed(
            title="🔍 Processing Batch...",
            description=f"Adding {len(new_usernames)} accounts to ban monitoring...",
            color=0xf1c40f
        ))
        
        success_count = 0
        failed_usernames = []
        
        for username in new_usernames:
            try:
                await asyncio.sleep(random.uniform(3, 6))
                status_code, _ = await self.instagram_api.fetch_profile(username)
                
                if status_code is not None:
                    self.ban_data_manager.add_account(username, message.channel.id, message.author.id)
                    success_count += 1
                    self.ban_monitor_service.start_monitoring(username, message.channel.id)
                else:
                    failed_usernames.append(username)
            except Exception as e:
                logger.error(f"Error processing @{username}: {e}")
                failed_usernames.append(username)
        
        result_parts = []
        if success_count > 0:
            result_parts.append(f"✅ **{success_count}** accounts added to ban monitoring")
        if already_monitoring:
            result_parts.append(f"⚠️ **{len(already_monitoring)}** already monitored")
        if failed_usernames:
            result_parts.append(f"❌ **{len(failed_usernames)}** failed")
        
        embed = discord.Embed(
            title="🔍 Ban Monitoring Batch Results",
            description="\n".join(result_parts),
            color=0x2ecc71 if success_count > 0 else 0xe74c3c
        )
        await processing_msg.edit(embed=embed)
    
    # ===== CLEAR COMMANDS =====
    
    async def handle_clearunban(self, message: discord.Message, args: str):
        """Handle !clearunban command"""
        # Handle !clearunban all
        if args and args.lower() == "all":
            if self.data_manager.get_account_count() == 0:
                embed = discord.Embed(
                    title="⚠️ No Accounts",
                    description="No accounts are currently being monitored for unbans.",
                    color=0xf1c40f
                )
                await message.channel.send(embed=embed)
                return
            
            count = self.data_manager.clear_all()
            self.monitor_service.stop_all_monitoring()
            
            embed = discord.Embed(
                title="🛑 All Unban Monitors Cleared",
                description=f"✅ Stopped monitoring **{count}** accounts for unbans.",
                color=0x2ecc71
            )
            await message.channel.send(embed=embed)
            return
        
        if not args:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!clearunban username` or `!clearunban username1 username2` or `!clearunban all`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        usernames = parse_usernames(args)
        stopped = []
        not_found = []
        
        for username in usernames:
            if self.data_manager.is_monitoring(username):
                self.monitor_service.stop_monitoring(username)
                stopped.append(username)
            else:
                not_found.append(username)
        
        result_parts = []
        if stopped:
            result_parts.append(f"✅ **Stopped:** {', '.join(f'@{u}' for u in stopped)}")
        if not_found:
            result_parts.append(f"❌ **Not found:** {', '.join(f'@{u}' for u in not_found)}")
        
        embed = discord.Embed(
            title="🛑 Unban Monitor Stop Results",
            description="\n".join(result_parts),
            color=0x2ecc71 if stopped else 0xf1c40f
        )
        await message.channel.send(embed=embed)
    
    async def handle_clearban(self, message: discord.Message, args: str):
        """Handle !clearban command"""
        # Handle !clearban all
        if args and args.lower() == "all":
            if self.ban_data_manager.get_account_count() == 0:
                embed = discord.Embed(
                    title="⚠️ No Accounts",
                    description="No accounts are currently being monitored for bans.",
                    color=0xf1c40f
                )
                await message.channel.send(embed=embed)
                return
            
            count = self.ban_data_manager.clear_all()
            self.ban_monitor_service.stop_all_monitoring()
            
            embed = discord.Embed(
                title="🛑 All Ban Monitors Cleared",
                description=f"✅ Stopped monitoring **{count}** accounts for bans.",
                color=0x2ecc71
            )
            await message.channel.send(embed=embed)
            return
        
        if not args:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!clearban username` or `!clearban username1 username2` or `!clearban all`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        usernames = parse_usernames(args)
        stopped = []
        not_found = []
        
        for username in usernames:
            if self.ban_data_manager.is_monitoring(username):
                self.ban_monitor_service.stop_monitoring(username)
                stopped.append(username)
            else:
                not_found.append(username)
        
        result_parts = []
        if stopped:
            result_parts.append(f"✅ **Stopped:** {', '.join(f'@{u}' for u in stopped)}")
        if not_found:
            result_parts.append(f"❌ **Not found:** {', '.join(f'@{u}' for u in not_found)}")
        
        embed = discord.Embed(
            title="🛑 Ban Monitor Stop Results",
            description="\n".join(result_parts),
            color=0x2ecc71 if stopped else 0xf1c40f
        )
        await message.channel.send(embed=embed)
    
    # ===== LIST COMMANDS =====
    
    async def handle_list(self, message: discord.Message):
        """Handle !list command"""
        unban_accounts = self.data_manager.get_all_accounts()
        ban_accounts = self.ban_data_manager.get_all_accounts()
        
        embed = discord.Embed(title="👁️ Monitored Accounts", color=0x1abc9c)
        
        # Unban monitoring list
        if unban_accounts:
            unban_list = []
            for username, data in unban_accounts.items():
                started = datetime.fromisoformat(data["started_at"])
                elapsed = datetime.now() - started
                unban_list.append(f"• **@{username}** ({format_elapsed_time(elapsed.total_seconds())})")
            
            embed.add_field(
                name="🔓 Unban Monitoring",
                value="\n".join(unban_list),
                inline=False
            )
        else:
            embed.add_field(
                name="🔓 Unban Monitoring",
                value="No accounts",
                inline=False
            )
        
        # Ban monitoring list
        if ban_accounts:
            ban_list = []
            for username, data in ban_accounts.items():
                started = datetime.fromisoformat(data["started_at"])
                elapsed = datetime.now() - started
                ban_list.append(f"• **@{username}** ({format_elapsed_time(elapsed.total_seconds())})")
            
            embed.add_field(
                name="🚫 Ban Monitoring",
                value="\n".join(ban_list),
                inline=False
            )
        else:
            embed.add_field(
                name="🚫 Ban Monitoring",
                value="No accounts",
                inline=False
            )
        
        await message.channel.send(embed=embed)
    
    # ===== SESSION MANAGEMENT COMMANDS (ADMIN) =====
    
    async def handle_add_session(self, message: discord.Message, args: str):
        """Handle !ads (add session) command"""
        if not is_admin(message.author.id, self.config.admin_user_ids):
            return
        
        if not args:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!ads <sessionid>`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        sessionid = args.strip()
        
        if self.session_manager.add_session(sessionid):
            embed = discord.Embed(
                title="✅ Session Added",
                description=f"Session added successfully!\nTotal sessions: **{self.session_manager.get_session_count()}**",
                color=0x2ecc71
            )
        else:
            embed = discord.Embed(
                title="⚠️ Session Already Exists",
                description="This session is already in the list.",
                color=0xf1c40f
            )
        
        await message.channel.send(embed=embed)
    
    async def handle_remove_session(self, message: discord.Message, args: str):
        """Handle !rms (remove session) command"""
        if not is_admin(message.author.id, self.config.admin_user_ids):
            return
        
        if not args:
            # Show list of sessions for removal
            sessions = self.session_manager.get_all_sessions()
            if not sessions:
                embed = discord.Embed(
                    title="⚠️ No Sessions",
                    description="No sessions available to remove.",
                    color=0xf1c40f
                )
                await message.channel.send(embed=embed)
                return
            
            session_list = "\n".join([f"{i+1}. `{s}`" for i, s in enumerate(sessions)])
            embed = discord.Embed(
                title="📋 Current Sessions",
                description=f"{session_list}\n\nUse: `!rms <sessionid>` to remove",
                color=0x3498db
            )
            await message.channel.send(embed=embed)
            return
        
        sessionid = args.strip()
        
        if self.session_manager.remove_session(sessionid):
            embed = discord.Embed(
                title="✅ Session Removed",
                description=f"Session removed successfully!\nRemaining sessions: **{self.session_manager.get_session_count()}**",
                color=0x2ecc71
            )
        else:
            embed = discord.Embed(
                title="❌ Session Not Found",
                description="This session doesn't exist in the list.",
                color=0xe74c3c
            )
        
        await message.channel.send(embed=embed)
    
    # ===== OTHER COMMANDS =====
    
    async def handle_ping(self, message: discord.Message):
        """Handle !ping command"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Bot is online and responsive!",
            color=0x2ecc71
        )
        await message.channel.send(embed=embed)
    
    async def handle_status(self, message: discord.Message):
        """Handle !status command (Admin only)"""
        if not is_admin(message.author.id, self.config.admin_user_ids):
            return
        
        proxy_status = "✅ CONFIGURED" if self.config.get_proxy_url() else "❌ NOT CONFIGURED"
        current_session = self.session_manager.get_current_session()
        session_preview = f"{current_session[:15]}...{current_session[-10:]}" if len(current_session) > 25 else current_session
        
        status_text = f"""
**Proxy:** {proxy_status}
**Gateway:** {self.config.proxy_gateway or 'N/A'}
**Sessions:** {self.session_manager.get_session_count()} active
**Current Session:** `{session_preview}`
**Screenshots:** {'✅ Enabled' if self.config.generate_screenshots else '❌ Disabled'}
**Check Interval:** {self.config.min_check_interval//60}-{self.config.max_check_interval//60} minutes
**Unban Monitors:** {self.data_manager.get_account_count()}/{self.max_monitor}
**Ban Monitors:** {self.ban_data_manager.get_account_count()}/{self.max_monitor}
**Mode:** Session-based with rotation
        """
        
        embed = discord.Embed(
            title="📊 Bot Status",
            description=status_text.strip(),
            color=0x3498db
        )
        await message.channel.send(embed=embed)
    
    async def handle_toggle_screenshot(self, message: discord.Message):
        """Handle !togglescreenshot command (Admin only)"""
        if not is_admin(message.author.id, self.config.admin_user_ids):
            return
        
        self.config.generate_screenshots = not self.config.generate_screenshots
        
        status = "ENABLED ✅" if self.config.generate_screenshots else "DISABLED ❌"
        embed = discord.Embed(
            title="📸 Screenshot Toggle",
            description=f"Screenshots are now **{status}**",
            color=0x2ecc71 if self.config.generate_screenshots else 0xe74c3c
        )
        await message.channel.send(embed=embed)
    
    async def handle_set_interval(self, message: discord.Message, args: str):
        """Handle !setinterval command (Admin only)"""
        if not is_admin(message.author.id, self.config.admin_user_ids):
            return
        
        parts = args.split()
        if len(parts) != 2:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!setinterval <min_minutes> <max_minutes>`\nExample: `!setinterval 3 7`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        try:
            min_min = int(parts[0])
            max_min = int(parts[1])
            
            if min_min < 1 or max_min < min_min:
                raise ValueError("Invalid range")
            
            self.config.min_check_interval = min_min * 60
            self.config.max_check_interval = max_min * 60
            
            embed = discord.Embed(
                title="✅ Interval Updated",
                description=f"Check interval set to **{min_min}-{max_min} minutes**",
                color=0x2ecc71
            )
            await message.channel.send(embed=embed)
        except ValueError:
            embed = discord.Embed(
                title="❌ Invalid Values",
                description="Please provide valid numbers (min < max, both > 0)",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
    
    async def handle_logs(self, message: discord.Message, log_file: str = "bot.log"):
        """Handle !logs command (Admin only)"""
        if not is_admin(message.author.id, self.config.admin_user_ids):
            return
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()
                recent_logs = ''.join(lines[-25:])
            
            if len(recent_logs) > 1900:
                recent_logs = recent_logs[-1900:]
            
            embed = discord.Embed(
                title="📋 Recent Logs",
                description=f"```\n{recent_logs}\n```",
                color=0x9b59b6
            )
            await message.channel.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="❌ Log Error",
                description=f"Could not read logs: {e}",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
    
    async def handle_test(self, message: discord.Message, args: str):
        """Handle !test command (Admin only) - Test notification with custom time"""
        
        if not args:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!test <username> <hours> <minutes> <seconds>`\nExample: `!test cristiano 2 30 45`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        parts = args.strip().split()
        if len(parts) != 4:
            embed = discord.Embed(
                title="❌ Usage Error",
                description="Use: `!test <username> <hours> <minutes> <seconds>`\nExample: `!test cristiano 2 30 45`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        test_username = parts[0].lower().replace('@', '')
        
        try:
            hours = int(parts[1])
            minutes = int(parts[2])
            seconds = int(parts[3])
            
            if hours < 0 or minutes < 0 or seconds < 0:
                raise ValueError("Time values must be positive")
            
            # Calculate total elapsed time in seconds
            total_elapsed = (hours * 3600) + (minutes * 60) + seconds
            
        except ValueError as e:
            embed = discord.Embed(
                title="❌ Invalid Time Values",
                description="Please provide valid numbers for hours, minutes, and seconds.\nExample: `!test cristiano 2 30 45`",
                color=0xe74c3c
            )
            await message.channel.send(embed=embed)
            return
        
        test_msg = await message.channel.send(embed=discord.Embed(
            title="🧪 Testing...",
            description=f"Fetching @{test_username} profile...",
            color=0xf1c40f
        ))
        
        import time
        start = time.time()
        status_code, data = await self.instagram_api.fetch_profile(test_username)
        fetch_time = time.time() - start
        
        if not data or not data.get("data", {}).get("user"):
            result = f"""
    ❌ **Failed**
    **Status:** {status_code or 'Timeout/Error'}
    **Fetch Time:** {fetch_time:.2f}s
    **Possible Issues:**
    - Account not found or suspended
    - Session expired/invalid
    - Proxy blocked
    - Bot detection
            """
            embed = discord.Embed(
                title="🧪 Test Failed",
                description=result.strip(),
                color=0xe74c3c
            )
            await test_msg.edit(embed=embed)
            return
        
        # Account found - prepare notification
        user = data["data"]["user"]
        followers = user.get("edge_followed_by", {}).get("count", 0)
        following = user.get("edge_follow", {}).get("count", 0)
        posts = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
        profile_pic_url = user.get("profile_pic_url_hd") or user.get("profile_pic_url")
        full_name = user.get("full_name", "")
        bio = user.get("biography", "")
        is_verified = user.get("is_verified", False)
        
        elapsed_str = format_elapsed_time(total_elapsed)
        instagram_url = f"https://instagram.com/{test_username}"
        
        message_text = (
            f"[Account Recovered | @{test_username}](<{instagram_url}>) 🏆✅\n"
            f"Followers: {followers:,} | Following: {following:,}\n"
            f"⏱️ Time Taken: {elapsed_str}"
        )
        
        await test_msg.delete()
        
        try:
            if self.config.generate_screenshots and profile_pic_url:
                # Download profile picture
                image_data = await self.instagram_api.download_profile_picture(profile_pic_url)
                
                # Load verification badge
                import os
                import asyncio
                img_dir = os.path.dirname(os.path.abspath(__file__))
                img_path = os.path.join(img_dir, 'bluetick.png')
                verification_badge = None
                try:
                    with open(img_path, 'rb') as f:
                        verification_badge = f.read()
                except Exception:
                    pass
                
                # Generate screenshot
                screenshot = await asyncio.to_thread(
                    self.monitor_service.screenshot_gen.create_screenshot,
                    test_username,
                    image_data,
                    followers,
                    following,
                    posts,
                    full_name,
                    bio,
                    is_verified,
                    verification_badge
                )
                
                if screenshot:
                    file = discord.File(screenshot, filename=f"{test_username}_profile.png")
                    embed = discord.Embed(color=0x2ecc71)
                    embed.set_image(url=f"attachment://{test_username}_profile.png")
                    await message.channel.send(embed=embed, file=file, content=message_text)
                else:
                    # Fallback to embed without screenshot
                    embed = discord.Embed(
                        title="Test Notification",
                        description=(
                            f"**[Account Recovered | @{test_username} 🏆](<{instagram_url}>)**\n"
                            f"**Followers:** {followers:,} ✅\n"
                            f"**Following:** {following:,}\n"
                            f"⏱️ **Time taken:** {elapsed_str}"
                        ),
                        color=0x2ecc71
                    )
                    await message.channel.send(embed=embed)
            else:
                # Screenshots disabled or no profile pic
                embed = discord.Embed(
                    title="Test Notification",
                    description=(
                        f"**[Account Recovered | @{test_username} 🏆](<{instagram_url}>)**\n"
                        f"**Followers:** {followers:,} ✅\n"
                        f"**Following:** {following:,}\n"
                        f"⏱️ **Time taken:** {elapsed_str}"
                    ),
                    color=0x2ecc71
                )
                await message.channel.send(embed=embed)
                
        except Exception as e:
            logger.error(f"Error sending test notification: {e}")
            await message.channel.send(content=message_text)
    
    async def handle_help(self, message: discord.Message):
        """Handle !help command"""
        help_text = """
**Unban Monitoring:**
`!unban <username>` - Monitor for account recovery
`!unban <user1> <user2>` - Monitor multiple
`!clearunban <username>` - Stop unban monitoring
`!clearunban all` - Stop all unban monitors

**Ban Monitoring:**
`!ban <username>` - Monitor for account ban
`!ban <user1> <user2>` - Monitor multiple
`!clearban <username>` - Stop ban monitoring
`!clearban all` - Stop all ban monitors

**General:**
`!list` - Show all monitored accounts
`!ping` - Check bot status
`!help` - Show this message
        """
        
        embed = discord.Embed(
            title="🤖 Bot Commands",
            description=help_text.strip(),
            color=0x1abc9c
        )
        await message.channel.send(embed=embed)
