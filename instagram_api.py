"""Instagram API interaction module with session management"""
import aiohttp
import asyncio
import random
import logging
import hashlib
import uuid
from typing import Optional, Tuple, Dict

logger = logging.getLogger("ig_monitor_bot")

# Latest Instagram Android user agents (Jan 2025)
USER_AGENTS = [
    "Instagram 315.0.0.42.97 Android (33/13; 480dpi; 1080x2400; Xiaomi; 2201123G; lisa; qcom; en_US; 560107895)",
    "Instagram 314.0.0.37.120 Android (32/12; 420dpi; 1080x2340; samsung; SM-G998B; p3s; exynos2100; en_US; 558642214)",
    "Instagram 313.1.0.37.104 Android (31/12; 440dpi; 1080x2400; OnePlus; LE2121; OnePlus9Pro; qcom; en_US; 557512458)",
    "Instagram 312.0.0.42.109 Android (33/13; 560dpi; 1440x3200; Xiaomi; M2012K11AG; venus; qcom; en_US; 555841423)",
    "Instagram 311.0.0.41.109 Android (30/11; 480dpi; 1080x2400; OPPO; CPH2207; OP4F2F; qcom; en_US; 554147875)",
]

class InstagramAPI:
    def __init__(self, session_manager, proxy_url: Optional[str] = None):
        self.session_manager = session_manager
        self.proxy_url = proxy_url
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def get_session(self):
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=2)
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        return self.session
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _generate_device_id(self) -> str:
        """Generate realistic Android device ID"""
        return str(uuid.uuid4())
    
    def _generate_headers(self, username: str, sessionid: str) -> Dict[str, str]:
        """Generate realistic Instagram mobile app headers with session cookie"""
        user_agent = random.choice(USER_AGENTS)
        device_id = self._generate_device_id()
        
        headers = {
            "User-Agent": user_agent,
            "X-IG-App-ID": "936619743392459",
            "X-IG-Device-ID": device_id,
            "X-IG-Android-ID": f"android-{hashlib.md5(device_id.encode()).hexdigest()[:16]}",
            "X-IG-App-Locale": "en_US",
            "X-IG-Device-Locale": "en_US",
            "X-IG-Mapped-Locale": "en_US",
            "X-IG-Connection-Type": "WIFI",
            "X-IG-Capabilities": "3brTv10=",
            "X-IG-App-Startup-Country": "US",
            "X-Bloks-Version-Id": hashlib.md5(str(int(asyncio.get_event_loop().time())).encode()).hexdigest()[:16],
            "X-IG-WWW-Claim": "0",
            "X-Bloks-Is-Layout-RTL": "false",
            "X-IG-Connection-Speed": f"{random.randint(1000, 3000)}kbps",
            "X-IG-Bandwidth-Speed-KBPS": str(random.uniform(2000.0, 5000.0)),
            "X-IG-Bandwidth-TotalBytes-B": str(random.randint(5000000, 10000000)),
            "X-IG-Bandwidth-TotalTime-MS": str(random.randint(200, 500)),
            "X-IG-EU-DC-ENABLED": "true",
            "X-IG-Extended-CDN-Thumbnail-Cache-Busting-Value": str(random.randint(1000, 9999)),
            "X-Mid": hashlib.md5(device_id.encode()).hexdigest()[:20],
            "Accept-Language": "en-US",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "Cookie": f"sessionid={sessionid}"
        }
        
        return headers
    
    async def fetch_profile(self, username: str, retry_count: int = 0, max_retries: int = 3) -> Tuple[Optional[int], Optional[Dict]]:
        """Fetch Instagram profile with session rotation on errors"""
        
        # Exponential backoff delay
        if retry_count > 0:
            delay = min(300, (2 ** retry_count) * 30 + random.uniform(10, 30))
            logger.info(f"Retry {retry_count}/{max_retries} for @{username} after {delay:.1f}s delay")
            await asyncio.sleep(delay)
        
        # Random delay before request (anti-pattern detection)
        await asyncio.sleep(random.uniform(2, 5))
        
        # Get current session
        current_sessionid = self.session_manager.get_current_session()
        headers = self._generate_headers(username, current_sessionid)
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        
        if not self.proxy_url:
            logger.error("No proxy configured! Please add proxy credentials to config.json")
            return None, None
        
        session = await self.get_session()
        
        try:
            async with session.get(url, headers=headers, proxy=self.proxy_url) as response:
                status = response.status
                
                logger.info(f"[@{username}] HTTP {status} via proxy (retry: {retry_count})")
                
                if status == 200 and username and ('data' in (await response.json()) and username.lower() == (await response.json())['data']['user']['username'].lower()):
                    try:
                        data = await response.json()
                        logger.info(f"[@{username}] ✅ Success - Profile fetched")
                        return status, data
                        print(data)
                    except Exception as e:
                        logger.error(f"[@{username}] JSON decode error: {e}")
                        return status, None
                if status == 200 :
                    try:
                        data = await response.json()
                        logger.info(f"[@{username}] response received, but username mismatch - possibly banned")
                        return status, data
                    except Exception as e:
                        logger.error(f"[@{username}] JSON decode error: {e}")
                        return status, None
                elif status == 404:
                    logger.info(f"[@{username}] Account not found / suspended (404)")
                    return status, None
                    
                elif status == 429:
                    logger.warning(f"[@{username}] Rate limited (429) - rotating session")
                    self.session_manager.rotate_session()
                    if retry_count < max_retries:
                        return await self.fetch_profile(username, retry_count + 1, max_retries)
                    return status, None
                    
                elif status in [400, 401]:
                    logger.warning(f"[@{username}] Auth error ({status}) - rotating session")
                    self.session_manager.rotate_session()
                    if retry_count < max_retries:
                        await asyncio.sleep(random.uniform(1, 5))
                        return await self.fetch_profile(username, retry_count + 1, max_retries)
                    return status, None
                    
                else:
                    logger.warning(f"[@{username}] Unexpected status {status}")
                    if retry_count < max_retries:
                        return await self.fetch_profile(username, retry_count + 1, max_retries)
                    return status, None
                    
        except asyncio.TimeoutError:
            logger.error(f"[@{username}] Timeout error")
            if retry_count < max_retries:
                return await self.fetch_profile(username, retry_count + 1, max_retries)
            return None, None
        except Exception as e:
            logger.error(f"[@{username}] Request error: {e}")
            if retry_count < max_retries:
                return await self.fetch_profile(username, retry_count + 1, max_retries)
            return None, None
    
    async def download_profile_picture(self, profile_pic_url: str) -> Optional[bytes]:
        """Download profile picture from URL"""
        try:
            session = await self.get_session()
            async with session.get(profile_pic_url, proxy=self.proxy_url) as response:
                if response.status == 200:
                    return await response.read()
        except Exception as e:
            logger.error(f"Error downloading profile picture: {e}")
        return None