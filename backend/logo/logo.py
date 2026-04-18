"""
DevMind Logo Generator - Retro Pixel-Art Style for Terminal
Creates and displays a retro pixel-art style logo in the CLI
"""

from PIL import Image, ImageDraw, ImageFont
import os
from io import BytesIO


def generate_devmind_logo_image(width: int = 600, height: int = 120) -> Image.Image:
    """
    Generate a retro pixel-art style DevMind logo as PIL Image.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        PIL Image object
    """
    # Colors inspired by retro arcade aesthetics
    background_color = (20, 20, 30)  # Dark blue-black
    main_color = (255, 223, 64)      # Bright gold/yellow
    glow_color = (255, 140, 40)      # Orange glow
    shadow_color = (200, 100, 0)     # Dark orange shadow
    
    # Create base image
    img = Image.new('RGB', (width, height), background_color)
    draw = ImageDraw.Draw(img, 'RGBA')
    
    # Add glow effect
    center_x = width // 2
    center_y = height // 2
    glow_radius = max(width, height) // 3
    
    for i in range(glow_radius, 0, -15):
        alpha = int(40 * (1 - i / glow_radius))
        draw.ellipse(
            [center_x - i, center_y - i // 2, center_x + i, center_y + i // 2],
            outline=(*glow_color, alpha)
        )
    
    # Get font
    font_size = int(height * 0.55)
    font = None
    font_paths = [
        "C:\\Windows\\Fonts\\ariblk.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                pass
    
    if font is None:
        font = ImageFont.load_default()
    
    text = "DEVMIND"
    
    # Get text bounding box to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2
    
    # Draw shadow
    shadow_offset = 2
    draw.text(
        (text_x + shadow_offset, text_y + shadow_offset),
        text,
        font=font,
        fill=shadow_color
    )
    
    # Draw outline for glow effect
    for adj_x in range(-2, 3):
        for adj_y in range(-2, 3):
            if adj_x != 0 or adj_y != 0:
                draw.text(
                    (text_x + adj_x, text_y + adj_y),
                    text,
                    font=font,
                    fill=(*glow_color, 80)
                )
    
    # Draw main text
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=main_color
    )
    
    # Add scanlines for retro effect
    for y in range(0, height, 3):
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, 15))
    
    return img


def display_logo_ascii():
    """
    Display ASCII art logo with retro styling.
    """
    from rich.console import Console
    from rich.text import Text
    
    console = Console()
    
    logo = """
    [bold yellow]╔═══════════════════════════════════════════╗[/bold yellow]
    [bold yellow]║[/bold yellow]  [bold yellow]██████╗ ███████╗██╗   ██╗███╗   ███╗██╗[/bold yellow]  [bold yellow]║[/bold yellow]
    [bold yellow]║[/bold yellow]  [bold yellow]██╔══██╗██╔════╝██║   ██║████╗ ████║██║[/bold yellow]  [bold yellow]║[/bold yellow]
    [bold yellow]║[/bold yellow]  [bold yellow]██║  ██║█████╗  ██║   ██║██╔████╔██║██║[/bold yellow]  [bold yellow]║[/bold yellow]
    [bold yellow]║[/bold yellow]  [bold yellow]██║  ██║██╔══╝  ╚██╗ ██╔╝██║╚██╔╝██║██║[/bold yellow]  [bold yellow]║[/bold yellow]
    [bold yellow]║[/bold yellow]  [bold yellow]██████╔╝███████╗ ╚████╔╝ ██║ ╚═╝ ██║██║[/bold yellow]  [bold yellow]║[/bold yellow]
    [bold yellow]║[/bold yellow]  [bold yellow]╚═════╝ ╚══════╝  ╚═══╝  ╚═╝     ╚═╝╚═╝[/bold yellow]  [bold yellow]║[/bold yellow]
    [bold yellow]╠═══════════════════════════════════════════╣[/bold yellow]
    [bold cyan]║  [dim]AI-Powered Code Analysis & Debugging  [/dim]    [bold yellow]║[/bold yellow]
    [bold yellow]╚═══════════════════════════════════════════╝[/bold yellow]
    """
    
    console.print(logo)


def display_logo_in_terminal():
    """
    Display the DevMind logo in the terminal using rich_pixels if available.
    Falls back to ASCII art if rich_pixels is not available.
    """
    try:
        from rich_pixels import Pixels
        from rich.console import Console
        
        console = Console()
        
        # Generate logo image
        logo_img = generate_devmind_logo_image(width=600, height=120)
        
        # Convert to smaller size for terminal
        logo_img.thumbnail((100, 25), Image.Resampling.LANCZOS)
        
        # Display using rich_pixels
        pixels = Pixels.from_image(logo_img)
        console.print(pixels)
        
        return True
    except (ImportError, Exception):
        # Fallback to ASCII art
        display_logo_ascii()
        return False


if __name__ == "__main__":
    # Test logo display
    display_logo_in_terminal()

