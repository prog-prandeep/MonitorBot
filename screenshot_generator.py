"""Screenshot generation module"""
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from typing import Optional

logger = logging.getLogger("ig_monitor_bot")

class ScreenshotGenerator:
    def __init__(self):
        self.width = 695
        self.height = 260
        self.background_color = '#000000'
        self.profile_pic_size = 170
        self.profile_pic_x = 12
        self.profile_pic_y = 12
        
        # Load fonts
        try:
            self.font_username = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            self.font_fullname = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.font_stats_number = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            self.font_stats_label = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            self.font_bio = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
            self.font_button = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
        except:
            logger.warning("Could not load custom fonts, using default")
            self.font_username = self.font_fullname = self.font_stats_number = ImageFont.load_default()
            self.font_stats_label = self.font_bio = self.font_button = ImageFont.load_default()
    
    @staticmethod
    def format_count(count: int) -> str:
        """Format follower/following count"""
        if count >= 1_000_000:
            return f"{count/1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count/1_000:.1f}K"
        return str(count)
    
    @staticmethod
    def _remove_emojis(text: str) -> str:
        """Remove emojis and special characters from text"""
        import re
        # Remove emojis and special unicode characters
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"  # supplemental symbols
            u"\U0001FA00-\U0001FA6F"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub('', text).strip()
    
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
    
    def _add_header(self, draw: ImageDraw, username: str, full_name: str, is_verified: bool, verification_badge: Optional[bytes]):
        """Add username, full name, verification badge and three-dot menu"""
        header_x = 200
        username_y = 18
        
        # Draw username
        draw.text((header_x, username_y), username, fill='#FFFFFF', font=self.font_username)
        
        # Add verification badge if verified and badge image is provided
        username_bbox = draw.textbbox((header_x, username_y), username, font=self.font_username)
        username_width = username_bbox[2] - username_bbox[0]
        
        badge_offset = 0
        if is_verified and verification_badge:
            try:
                # Load and resize verification badge
                badge_size = 35
                badge_img = Image.open(BytesIO(verification_badge)).convert('RGBA')
                badge_img = badge_img.resize((badge_size, badge_size), Image.LANCZOS)
                
                # Position badge next to username
                badge_x = header_x + username_width + 8
                badge_y = username_y
                
                # Paste badge with transparency
                img = draw._image
                img.paste(badge_img, (badge_x, badge_y), badge_img)
                
                badge_offset = badge_size + 8
            except Exception as e:
                logger.error(f"Error adding verification badge: {e}")
        
        # Draw three-dot menu
        menu_x = header_x + username_width + badge_offset + 12
        menu_y = username_y + 12
        for i in range(3):
            draw.ellipse(
                (menu_x + i*7 - 2.5, menu_y - 2.5, menu_x + i*7 + 2.5, menu_y + 2.5), 
                fill='#FFFFFF'
            )
        
        # Draw full name below username with proper spacing (only if exists)
        display_name = full_name if full_name and full_name.strip() else ""
        if display_name:
            # Remove emojis from display name
            display_name = self._remove_emojis(display_name)
            # Ensure full name doesn't overlap with stats - draw it closer to username
            draw.text((header_x, username_y + 32), display_name, fill='#FFFFFF', font=self.font_fullname)
    
    def _add_stats(self, draw: ImageDraw, followers: int, following: int, posts: int):
        """Add follower/following/posts stats with FIXED position - large numbers on top, labels below"""
        # FIXED position - stats always appear here regardless of bio
        stats_y = 80
        header_x = 200
        spacing = 155
        
        # Posts - left column
        posts_x = header_x
        draw.text((posts_x, stats_y), str(posts), fill='#FFFFFF', font=self.font_stats_number)
        draw.text((posts_x, stats_y + 28), "posts", fill='#A8A8A8', font=self.font_stats_label)
        
        # Followers - middle column
        followers_x = posts_x + spacing
        draw.text((followers_x, stats_y), self.format_count(followers), fill='#FFFFFF', font=self.font_stats_number)
        draw.text((followers_x, stats_y + 28), "followers", fill='#A8A8A8', font=self.font_stats_label)
        
        # Following - right column
        following_x = followers_x + spacing
        draw.text((following_x, stats_y), str(following), fill='#FFFFFF', font=self.font_stats_number)
        draw.text((following_x, stats_y + 28), "following", fill='#A8A8A8', font=self.font_stats_label)
    
    def _add_bio(self, draw: ImageDraw, username: str, bio: str):
        """Add bio text with username handle at FIXED position"""
        # FIXED position - bio always appears here regardless of content
        bio_y = 135
        header_x = 200
        max_width = 490
        
        if bio and bio.strip():
            # Remove emojis from bio
            bio_clean = self._remove_emojis(bio)
            
            # Only take first sentence or limit to reasonable length
            sentences = bio_clean.split('.')
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 100:
                first_sentence = first_sentence[:100].strip()
            
            # Word wrap the first sentence only
            words = first_sentence.split()
            lines = []
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=self.font_bio)
                if bbox[2] - bbox[0] <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw only first line of bio
            if lines:
                draw.text((header_x, bio_y), lines[0], fill='#FFFFFF', font=self.font_bio)
                
                # Add "more" if there's more content
                if len(lines) > 1 or len(sentences) > 1:
                    line_bbox = draw.textbbox((header_x, bio_y), lines[0], font=self.font_bio)
                    more_x = line_bbox[2] + 5
                    draw.text((more_x, bio_y), "/", fill='#8E8E8E', font=self.font_bio)
            
            # Add username handle below bio
            handle_y = bio_y + 25
            draw.text((header_x, handle_y), f"@{username}", fill='#FFFFFF', font=self.font_bio)
    
    def _add_buttons(self, draw: ImageDraw):
        """Add Follow and Message buttons at bottom"""
        button_y = 207
        button_height = 38
        button_radius = 8
        
        # Follow button
        follow_x = 12
        follow_width = 332
        draw.rounded_rectangle(
            (follow_x, button_y, follow_x + follow_width, button_y + button_height),
            radius=button_radius,
            fill='#0095F6'
        )
        follow_text = "Follow"
        bbox = draw.textbbox((0, 0), follow_text, font=self.font_button)
        text_x = follow_x + (follow_width - (bbox[2] - bbox[0])) // 2
        text_y = button_y + (button_height - (bbox[3] - bbox[1])) // 2 - 1
        draw.text((text_x, text_y), follow_text, fill='#FFFFFF', font=self.font_button)
        
        # Message button
        message_x = follow_x + follow_width + 8
        message_width = 332
        draw.rounded_rectangle(
            (message_x, button_y, message_x + message_width, button_y + button_height),
            radius=button_radius,
            fill='#363636'
        )
        message_text = "Message"
        bbox = draw.textbbox((0, 0), message_text, font=self.font_button)
        text_x = message_x + (message_width - (bbox[2] - bbox[0])) // 2
        text_y = button_y + (button_height - (bbox[3] - bbox[1])) // 2 - 1
        draw.text((text_x, text_y), message_text, fill='#FFFFFF', font=self.font_button)
    
    def create_screenshot(
        self, 
        username: str, 
        image_data: Optional[bytes],
        followers: int,
        following: int,
        posts: int,
        full_name: str,
        bio: str,
        is_verified: bool = False,
        verification_badge: Optional[bytes] = None
    ) -> Optional[BytesIO]:
        """Create Instagram profile screenshot
        
        Args:
            username: Instagram username
            image_data: Profile picture image bytes
            followers: Number of followers
            following: Number of following
            posts: Number of posts
            full_name: Full display name
            bio: Bio text
            is_verified: Whether the account is verified
            verification_badge: Verification badge image bytes (PNG with transparency)
        """
        try:
            # Create base image
            img = Image.new('RGB', (self.width, self.height), color=self.background_color)
            draw = ImageDraw.Draw(img)
            
            # Store img reference in draw for badge pasting
            draw._image = img
            
            # Add all elements
            self._add_profile_picture(img, draw, image_data)
            self._add_header(draw, username, full_name, is_verified, verification_badge)
            self._add_stats(draw, followers, following, posts)
            self._add_bio(draw, username, bio)
            self._add_buttons(draw)
            
            # Save to buffer
            output_buffer = BytesIO()
            img.save(output_buffer, format='PNG', optimize=True, quality=100)
            output_buffer.seek(0)
            
            return output_buffer
            
        except Exception as e:
            logger.error(f"Error creating screenshot: {e}")
            return None