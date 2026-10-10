import os
import sys

from .ctk_font import CTkFont
from .font_manager import FontManager

# import DrawEngine to set preferred_drawing_method if loading shapes font fails
from ..core_rendering import DrawEngine

FontManager.init_font_manager()

# load Roboto fonts (used on Windows/Linux)
customtkinter_directory = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
FontManager.load_font(os.path.join(customtkinter_directory, "assets", "fonts", "Roboto", "Roboto-Regular.ttf"))
FontManager.load_font(os.path.join(customtkinter_directory, "assets", "fonts", "Roboto", "Roboto-Medium.ttf"))

# load font necessary for rendering the widgets (used on Windows/Linux)
if FontManager.load_font(os.path.join(customtkinter_directory, "assets", "fonts", "CustomTkinter_shapes_font.otf")) is False:
    # change draw method if font loading failed
    if DrawEngine.preferred_drawing_method == "font_shapes":
        DrawEngine.preferred_drawing_method = "circle_shapes"
