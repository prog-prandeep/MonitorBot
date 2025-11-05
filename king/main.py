"""Main bot entry point - Fixed for systemd services"""
import logging
import discord
import asyncio
import sys
import os

# Get the directory where this main.py is located (client folder)
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Get the parent directory (Bot folder with modules)
PARENT_DIR = os.path.dirname(CLIENT_DIR)

# Add parent directory to Python path so imports work
sys.path.insert(0, PARENT_DIR)

# Change working directory to client folder (for config.json, logs, etc.)
os.chdir(CLIENT_DIR)

# Now import modules (after fixing the path)
from config_manager import ConfigManager
from data_manager import DataManager
from ban_data_manager import BanDataManager
from session_manager import SessionManager
from instagram_api import InstagramAPI
from screenshot_generator import ScreenshotGenerator
from monitor_service import MonitorService
from ban_monitor_service import BanMonitorService
from command_handler import CommandHandler

# Constants
MAX_MONITOR = 15
LOG_FILE = "bot.log"  # Will be created in client folder

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ig_monitor_bot")

# Initialize Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Initialize components (all files will be in client folder now)
config = ConfigManager("config.json")  # client1/config.json
data_manager = DataManager("monitoring.json")  # client1/monitoring.json
ban_data_manager = BanDataManager("ban_monitor.json")  # client1/ban_monitor.json
session_manager = SessionManager("session.json")  # client1/session.json
instagram_api = InstagramAPI(session_manager, proxy_url=config.get_proxy_url())
screenshot_gen = ScreenshotGenerator()
monitor_service = MonitorService(instagram_api, data_manager, screenshot_gen, client, config)
ban_monitor_service = BanMonitorService(instagram_api, ban_data_manager, client, config)
command_handler = CommandHandler(
    monitor_service, 
    ban_monitor_service,
    data_manager, 
    ban_data_manager,
    instagram_api, 
    session_manager,
    config, 
    MAX_MONITOR
)

@client.event
async def on_ready():
    """Bot startup event"""
    logger.info(f"Bot logged in as {client.user}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Session-based mode: ENABLED")
    logger.info(f"Active sessions: {session_manager.get_session_count()}")
    logger.info(f"Screenshot feature: {'ENABLED' if config.generate_screenshots else 'DISABLED'}")
    logger.info(f"Check interval: {config.min_check_interval//60}-{config.max_check_interval//60} minutes")
    
    if not config.get_proxy_url():
        logger.error("⚠️ WARNING: No proxy configured! Bot will likely fail.")
    
    if session_manager.get_session_count() == 0:
        logger.warning("⚠️ WARNING: No sessions loaded, using fallback session")
    
    # Resume monitoring for existing accounts
    monitor_service.resume_all_monitoring()
    ban_monitor_service.resume_all_monitoring()

@client.event
async def on_message(message: discord.Message):
    """Handle incoming Discord messages"""
    if message.author.bot:
        return
    
    content = message.content.strip()
    
    # Parse command and arguments
    if not content.startswith("!"):
        return
    
    parts = content.split(maxsplit=1)
    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""
    
    # Route commands
    try:
        # Unban monitoring commands
        if command == "!unban":
            await command_handler.handle_unban(message, args)
        
        elif command == "!clearunban":
            await command_handler.handle_clearunban(message, args)
        
        # Ban monitoring commands
        elif command == "!ban":
            await command_handler.handle_ban(message, args)
        
        elif command == "!clearban":
            await command_handler.handle_clearban(message, args)
        
        # General commands
        elif command == "!list":
            await command_handler.handle_list(message)
        
        elif command == "!ping":
            await command_handler.handle_ping(message)
        
        # Admin commands
        elif command == "!status":
            await command_handler.handle_status(message)
        
        elif command == "!togglescreenshot":
            await command_handler.handle_toggle_screenshot(message)
        
        elif command == "!setinterval":
            await command_handler.handle_set_interval(message, args)
        
        elif command == "!logs":
            await command_handler.handle_logs(message, LOG_FILE)
        
        elif command == "!test":
            await command_handler.handle_test(message, args)
        
        # Session management commands (admin)
        elif command == "!ads":
            await command_handler.handle_add_session(message, args)
        
        elif command == "!rms":
            await command_handler.handle_remove_session(message, args)
        
        elif command == "!help":
            await command_handler.handle_help(message)
    
    except Exception as e:
        logger.error(f"Error handling command {command}: {e}")
        embed = discord.Embed(
            title="❌ Command Error",
            description=f"An error occurred while processing your command.",
            color=0xe74c3c
        )
        await message.channel.send(embed=embed)

async def cleanup():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down bot...")
    monitor_service.stop_all_monitoring()
    ban_monitor_service.stop_all_monitoring()
    await instagram_api.close()
    await client.close()

def main():
    """Main entry point"""
    try:
        client.run(config.discord_token)
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        asyncio.run(cleanup())

if __name__ == "__main__":
    main()