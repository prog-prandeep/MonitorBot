"""Screenshot generation module"""
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

logger = logging.getLogger("ig_monitor_bot")

class ScreenshotGenerator:
    def __init__(self):
        self.width = 1335
        self.height = 450
        self.background_color = '#000000'
        self.profile_pic_size = 270
        self.profile_pic_x = 45
        self.profile_pic_y = 90
        
        # Load fonts
        try:
            self.font_username = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 45)
            self.font_button = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
            self.font_stats_number = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
            self.font_stats_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 33)
            self.font_bio = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 33)
            self.font_fullname = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            logger.warning("Could not load custom fonts, using default")
            self.font_username = self.font_button = self.font_stats_number = ImageFont.load_default()
            self.font_stats_label = self.font_bio = self.font_fullname = ImageFont.load_default()
    
    @staticmethod
    def format_count(count: int) -> str:
        """Format follower/following count"""
        if count >= 1_000_000:
            return f"{count/1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count/1_000:.1f}K"
        return str(count)
    
    def _add_profile_picture(self, img: Image, draw: ImageDraw, image_data: Optional[bytes]):
        """Add profile picture to screenshot"""
        if image_data:
            try:
                profile_pic = Image.open(BytesIO(image_data)).resize(
                    (self.profile_pic_size, self.profile_pic_size)
                )
                
                # Create circular mask
                mask = Image.new('L', (self.profile_pic_size, self.profile_pic_size), 0)
                ImageDraw.Draw(mask).ellipse(
                    (0, 0, self.profile_pic_size, self.profile_pic_size), 
                    fill=255
                )
                
                # Apply mask
                output = Image.new('RGBA', (self.profile_pic_size, self.profile_pic_size), (0, 0, 0, 0))
                output.paste(profile_pic, (0, 0))
                output.putalpha(mask)
                
                img.paste(output, (self.profile_pic_x, self.profile_pic_y), output)
            except Exception as e:
                logger.error(f"Error processing profile picture: {e}")
                self._draw_placeholder_picture(draw)
        else:
            self._draw_placeholder_picture(draw)
    
    def _draw_placeholder_picture(self, draw: ImageDraw):
        """Draw placeholder for profile picture"""
        draw.ellipse(
            (self.profile_pic_x, self.profile_pic_y, 
             self.profile_pic_x + self.profile_pic_size, 
             self.profile_pic_y + self.profile_pic_size),
            fill='#262626', 
            outline='#555555', 
            width=6
        )
    
    def _add_username_and_button(self, draw: ImageDraw, username: str):
        """Add username and follow button"""
        username_x = 390
        username_y = 75
        
        # Draw username
        draw.text((username_x, username_y), username, fill='#FFFFFF', font=self.font_username)
        
        # Calculate button position
        username_bbox = draw.textbbox((username_x, username_y), username, font=self.font_username)
        username_width = username_bbox[2] - username_bbox[0]
        
        button_x = username_x + username_width + 40
        button_y = username_y
        button_width = 195
        button_height = 81
        
        # Draw follow button
        draw.rounded_rectangle(
            (button_x, button_y, button_x + button_width, button_y + button_height),
            radius=12, 
            fill='#0095F6'
        )
        
        # Add "Follow" text
        follow_text = "Follow"
        bbox = draw.textbbox((0, 0), follow_text, font=self.font_button)
        text_x = button_x + (button_width - (bbox[2] - bbox[0])) // 2
        text_y = button_y + (button_height - (bbox[3] - bbox[1])) // 2 - 6
        draw.text((text_x, text_y), follow_text, fill='#FFFFFF', font=self.font_button)
        
        # Draw menu dots
        menu_x = button_x + button_width + 30
        menu_y = button_y + 30
        for i in range(3):
            draw.ellipse(
                (menu_x + i*24 - 9, menu_y - 9, menu_x + i*24 + 9, menu_y + 9), 
                fill='#FFFFFF'
            )
    
    def _add_stats(self, draw: ImageDraw, followers: int, following: int, posts: int):
        """Add follower/following/posts stats"""
        stats_y = 165
        stats_spacing = 300
        username_x = 390
        
        # Posts
        posts_x = username_x
        draw.text((posts_x, stats_y), str(posts), fill='#FFFFFF', font=self.font_stats_number)
        draw.text((posts_x, stats_y + 48), "posts", fill='#8E8E8E', font=self.font_stats_label)
        
        # Followers
        followers_x = posts_x + stats_spacing
        draw.text((followers_x, stats_y), self.format_count(followers), fill='#FFFFFF', font=self.font_stats_number)
        draw.text((followers_x, stats_y + 48), "followers", fill='#8E8E8E', font=self.font_stats_label)
        
        # Following
        following_x = followers_x + stats_spacing
        draw.text((following_x, stats_y), self.format_count(following), fill='#FFFFFF', font=self.font_stats_number)
        draw.text((following_x, stats_y + 48), "following", fill='#8E8E8E', font=self.font_stats_label)
    
    def _add_name_and_bio(self, draw: ImageDraw, username: str, full_name: str, bio: str):
        """Add full name and bio"""
        bio_y = 285
        username_x = 390
        
        display_name = full_name if full_name and full_name.strip() else username
        draw.text((username_x, bio_y), username, fill='#FFFFFF', font=self.font_fullname)
    
    def create_screenshot(
        self, 
        username: str, 
        image_data: Optional[bytes],
        followers: int,
        following: int,
        posts: int,
        full_name: str,
        bio: str
    ) -> Optional[BytesIO]:
        """Create Instagram profile screenshot"""
        try:
            # Create base image
            img = Image.new('RGB', (self.width, self.height), color=self.background_color)
            draw = ImageDraw.Draw(img)
            
            # Add all elements
            self._add_profile_picture(img, draw, image_data)
            self._add_username_and_button(draw, username)
            self._add_stats(draw, followers, following, posts)
            self._add_name_and_bio(draw, username, full_name, bio)
            
            # Save to buffer
            output_buffer = BytesIO()
            img.save(output_buffer, format='PNG', optimize=True, quality=100)
            output_buffer.seek(0)
            
            return output_buffer
            
        except Exception as e:
            logger.error(f"Error creating screenshot: {e}")
            return None