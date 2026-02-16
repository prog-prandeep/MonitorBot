"""Instagram API interaction module with session management and advanced fingerprint evasion"""
import asyncio
import random
import logging
import hashlib
import uuid
import time
from typing import Optional, Tuple, Dict
from curl_cffi.requests import AsyncSession

logger = logging.getLogger("ig_monitor_bot")

# Latest real browser user agents (Updated 2025)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]

# Browser impersonation options for curl_cffi (verified supported versions)
BROWSER_VERSIONS = [
    "chrome120",
    "chrome119",
    "chrome116",
    "chrome110",
    "chrome107",
]


class InstagramAPI:
    def __init__(self, session_manager, proxy_url: Optional[str] = None):
        self.session_manager = session_manager
        self.proxy_url = proxy_url
        self.request_count = 0
    
    def _get_browser_version(self) -> str:
        """Get random browser version for impersonation"""
        return random.choice(BROWSER_VERSIONS)
    
    def _generate_headers(self, sessionid: str) -> Dict[str, str]:
        """Generate realistic web browser headers with session cookie"""
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "X-IG-App-ID": "936619743392459",
            "X-IG-WWW-Claim": "0",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"sessionid={sessionid}",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Referer": "https://www.instagram.com/",
            "Origin": "https://www.instagram.com",
            "Connection": "keep-alive",
        }
        
        return headers
    
    async def fetch_profile(
        self, 
        username: str, 
        retry_count: int = 0, 
        max_retries: int = 3
    ) -> Tuple[Optional[int], Optional[Dict]]:
        """Fetch Instagram profile with session rotation on errors and fingerprint evasion"""
        
        # Reduced exponential backoff delay
        if retry_count > 0:
            delay = min(60, (2 ** retry_count) * 5 + random.uniform(2, 5))
            logger.info(f"Retry {retry_count}/{max_retries} for @{username} after {delay:.1f}s delay")
            await asyncio.sleep(delay)
        
        # Random anti-pattern delay (reduced)
        await asyncio.sleep(random.uniform(1, 3))
        
        # Get current session
        current_sessionid = self.session_manager.get_current_session()
        browser = self._get_browser_version()
        headers = self._generate_headers(current_sessionid)
        url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
        
        if not self.proxy_url:
            logger.error("No proxy configured! Please add proxy credentials to config.json")
            return None, None
        
        self.request_count += 1
        logger.info(f"🚀 Request #{self.request_count} | @{username} | Browser: {browser} | Retry: {retry_count}/{max_retries}")
        
        try:
            async with AsyncSession() as session:
                response = await session.get(
                    url,
                    headers=headers,
                    proxies={"http": self.proxy_url, "https": self.proxy_url},
                    timeout=30,
                    impersonate=browser,
                    verify=False,
                    allow_redirects=True
                )
                
                status = response.status_code
                logger.info(f"[@{username}] HTTP {status} via proxy (browser: {browser})")
                
                if status == 200:
                    try:
                        data = response.json()
                        if 'data' in data and 'user' in data['data']:
                            response_username = data['data']['user'].get('username', '').lower()
                            if username.lower() == response_username:
                                logger.info(f"[@{username}] ✅ Success - Profile fetched")
                                return status, data
                            else:
                                logger.info(f"[@{username}] response received, but username mismatch - possibly banned")
                                return status, data
                        else:
                            logger.warning(f"[@{username}] Unexpected response structure")
                            return status, data
                    except Exception as e:
                        logger.error(f"[@{username}] JSON decode error: {e}")
                        if retry_count < max_retries:
                            return await self.fetch_profile(username, retry_count + 1, max_retries)
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
                        await asyncio.sleep(random.uniform(1, 3))
                        return await self.fetch_profile(username, retry_count + 1, max_retries)
                    return status, None
                
                elif status == 502:
                    logger.warning(f"[@{username}] Proxy error (502) - Bad Gateway")
                    if retry_count < max_retries:
                        await asyncio.sleep(random.uniform(3, 6))
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
            logger.error(f"[@{username}] Request error: {type(e).__name__} - {e}")
            if retry_count < max_retries:
                return await self.fetch_profile(username, retry_count + 1, max_retries)
            return None, None
    
    async def download_profile_picture(
        self, 
        profile_pic_url: str, 
        retry_count: int = 0, 
        max_retries: int = 5
    ) -> Optional[bytes]:
        """Download profile picture from URL with curl_cffi and extended retry logic"""
        
        if retry_count > 0:
            # Reduced delays for retries
            if retry_count <= 2:
                delay = random.uniform(2, 4)
            else:
                delay = random.uniform(5, 8)
            
            logger.info(f"Retrying profile picture download (attempt {retry_count}/{max_retries}) after {delay:.1f}s")
            await asyncio.sleep(delay)
        
        try:
            browser = self._get_browser_version()
            
            # Proper headers for image download
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": "https://www.instagram.com/",
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "cross-site",
            }
            
            logger.info(f"📸 Downloading profile picture (browser: {browser})")
            
            async with AsyncSession() as session:
                response = await session.get(
                    profile_pic_url,
                    headers=headers,
                    proxies={"http": self.proxy_url, "https": self.proxy_url} if self.proxy_url else None,
                    timeout=45,
                    impersonate=browser,
                    verify=False
                )
                
                status = response.status_code
                
                if status == 200:
                    content = response.content
                    if len(content) > 100:
                        logger.info(f"✅ Successfully downloaded profile picture ({len(content)} bytes)")
                        return content
                    else:
                        logger.warning(f"Downloaded content too small ({len(content)} bytes)")
                        if retry_count < max_retries:
                            return await self.download_profile_picture(profile_pic_url, retry_count + 1, max_retries)
                
                elif status == 402:
                    # Payment required - proxy bandwidth issue (temporary)
                    logger.warning(f"Proxy returned 402 (Payment Required) - bandwidth check, retrying...")
                    if retry_count < max_retries:
                        await asyncio.sleep(random.uniform(6, 10))
                        return await self.download_profile_picture(profile_pic_url, retry_count + 1, max_retries)
                    else:
                        logger.error("Failed to download after multiple 402 errors")
                        return None
                
                else:
                    logger.warning(f"Failed to download profile picture: HTTP {status}")
                    if retry_count < max_retries:
                        return await self.download_profile_picture(profile_pic_url, retry_count + 1, max_retries)
                        
        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading profile picture")
            if retry_count < max_retries:
                return await self.download_profile_picture(profile_pic_url, retry_count + 1, max_retries)
        except Exception as e:
            logger.error(f"Error downloading profile picture: {type(e).__name__} - {e}")
            if retry_count < max_retries:
                return await self.download_profile_picture(profile_pic_url, retry_count + 1, max_retries)
        
        return None