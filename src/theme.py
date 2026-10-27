"""pygame-gui theme: bundled Noto fonts and a dark palette."""
import paths


def build_theme() -> dict:
    fdir = paths.resource_path("assets", "fonts")
    reg, bold_path = str(fdir / "NotoSans-Regular.ttf"), str(fdir / "NotoSans-Bold.ttf")
    def font(size, bold=False):  # pygame-gui wants sizes as strings and fonts per element type
        return {"name": "noto_sans", "size": str(size), "bold": int(bold), "regular_path": reg, "bold_path": bold_path}

    colours = {"normal_bg": "#2b2b33", "hovered_bg": "#3b3b47", "disabled_bg": "#222228",
               "selected_bg": "#4a6fa5", "active_bg": "#4a6fa5", "dark_bg": "#1c1c22",
               "normal_text": "#e8e8ee", "hovered_text": "#ffffff", "selected_text": "#ffffff",
               "disabled_text": "#77777f", "normal_border": "#555560", "hovered_border": "#8888a0",
               "text_cursor": "#ffffff", "filled_bar": "#4a6fa5", "unfilled_bar": "#2b2b33"}
    theme = {"defaults": {"colours": colours}, "#title": {"font": font(30, True)}}
    for element in ("label", "button", "drop_down_menu", "selection_list", "text_entry_line", "text_box"):
        theme[element] = {"font": font(16)}
    return theme
