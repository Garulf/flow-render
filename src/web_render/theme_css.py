import math
import re

from .theme_parser import FALLBACK_RESOURCES

NAMED_COLORS = {
    'white': '#FFFFFF',
    'black': '#000000',
    'gray': '#808080',
    'red': '#FF0000',
}


def thickness_to_css(value: str) -> str:
    parts = value.replace(',', ' ').split()
    if len(parts) == 1:
        return f"{parts[0]}px"
    if len(parts) == 2:
        horizontal, vertical = parts
        return f"{vertical}px {horizontal}px"
    left, top, right, bottom = parts
    return ' '.join(part if part == '0' else f"{part}px"
                    for part in (top, right, bottom, left))


def flatten_color(value: str, background: str) -> str:
    value = value.strip()
    if value.lower() == 'transparent':
        return background
    if not value.startswith('#'):
        return NAMED_COLORS.get(value.lower(), value)
    digits = value[1:]
    if len(digits) != 8:
        return value
    alpha = int(digits[:2], 16) / 255
    foreground = tuple(int(digits[i:i + 2], 16) for i in (2, 4, 6))
    backdrop = tuple(int(background[1:][i:i + 2], 16) for i in (0, 2, 4))
    blended = tuple(round(alpha * f + (1 - alpha) * b)
                    for f, b in zip(foreground, backdrop))
    return '#{:02X}{:02X}{:02X}'.format(*blended)


def radius_to_css(value: str) -> str:
    parts = value.replace(',', ' ').split()
    return ' '.join(f"{part}px" for part in parts)


def gradient_to_css(start: str, end: str, stops) -> str:
    x0, y0 = (float(n) for n in start.replace(',', ' ').split())
    x1, y1 = (float(n) for n in end.replace(',', ' ').split())
    # WPF points are top-left origin with y down; CSS 0deg points up.
    angle = round(math.degrees(math.atan2(x1 - x0, -(y1 - y0)))) % 360
    rendered_stops = ', '.join(
        f"{color} {round(offset * 100)}%" for color, offset in stops)
    return f"linear-gradient({angle}deg, {rendered_stops})"


from pathlib import Path

LAYOUT_SHEET = Path(__file__).parent / 'theme_layout.css'

GRADIENT_MARKER = re.compile(r'\{Gradient (\S+)\|(\S+)\|(.+)\}')

PROPERTY_MAP = [
    ('WindowBorderStyle', 'Background', '#WindowBorder', 'background-color', 'color'),
    ('WindowBorderStyle', 'BorderBrush', '#WindowBorder', 'border-color', 'color'),
    ('QueryBoxStyle', 'Foreground', '#QueryBoxText', 'color', 'color'),
    ('QueryBoxStyle', 'FontSize', '#QueryBoxText', 'font-size', 'px'),
    ('QueryBoxStyle', 'CaretBrush', '#QueryBoxText::after', 'background', 'color'),
    ('QueryBoxStyle', 'FontSize', '#QueryBoxSuggestion', 'font-size', 'px'),
    ('QuerySuggestionBoxStyle', 'Foreground', '#QueryBoxSuggestion', 'color', 'color'),
    ('QueryBoxStyle', 'Height', '#QueryBoxArea', 'height', 'px'),
    ('ItemTitleStyle', 'Foreground', '.Title', 'color', 'color'),
    ('ItemTitleStyle', 'FontSize', '.Title', 'font-size', 'px'),
    ('ItemSubTitleStyle', 'Foreground', '.SubTitle', 'color', 'color'),
    ('ItemSubTitleStyle', 'FontSize', '.SubTitle', 'font-size', 'px'),
    ('ItemTitleSelectedStyle', 'Foreground', '.selecteditem .Title', 'color', 'color'),
    ('ItemSubTitleSelectedStyle', 'Foreground', '.selecteditem .SubTitle', 'color', 'color'),
    ('ItemBulletSelectedStyle', 'Background', '.selecteditem::before', 'background-color', 'color'),
    ('ItemBulletSelectedStyle', 'Width', '.selecteditem::before', 'width', 'px'),
    ('ItemBulletSelectedStyle', 'Height', '.selecteditem::before', 'height', 'px'),
    ('ItemBulletSelectedStyle', 'CornerRadius', '.selecteditem::before', 'border-radius', 'radius'),
    ('SeparatorStyle', 'Fill', '#Separator', 'background-color', 'color'),
    ('SeparatorStyle', 'Margin', '#Separator', 'margin', 'thickness'),
    ('ItemHotkeyStyle', 'Foreground', '.Hotkey', 'color', 'color'),
    ('ItemHotkeyStyle', 'FontSize', '.Hotkey', 'font-size', 'px'),
    ('ItemHotkeyBGStyle', 'Background', '.Hotkey', 'background-color', 'color'),
    ('ItemHotkeyBGSelectedStyle', 'Background', '.selecteditem .Hotkey', 'background-color', 'color'),
    ('SearchIconStyle', 'Fill', '#GlassIcon', 'color', 'color'),
]

RESOURCE_MAP = [
    ('ItemRadius', '.item', 'border-radius', 'radius'),
    ('ResultItemHeight', '.item', 'height', 'px'),
    ('ItemMargin', '.item', 'margin', 'thickness'),
    ('WindowRadius', '#WindowBorder', 'border-radius', 'radius'),
]


def transform(value: str, kind: str, window_bg: str) -> str:
    gradient = GRADIENT_MARKER.match(value)
    if gradient:
        stops = [(flatten_color(color, window_bg), float(offset))
                 for color, offset in (stop.split('@') for stop in gradient.group(3).split(';'))]
        return gradient_to_css(gradient.group(1), gradient.group(2), stops)
    if kind == 'color':
        return flatten_color(value, window_bg)
    if kind == 'px':
        return f"{value}px"
    if kind == 'radius':
        return radius_to_css(value)
    if kind == 'thickness':
        return thickness_to_css(value)
    return value


def selected_row_rule(theme, window_bg: str):
    value = (theme.resources.get('ItemSelectedBackgroundColor')
             or theme.styles.get('ItemSelectedBackgroundColor', {}).get('Color'))
    if value:
        return ('.selecteditem', 'background-color', flatten_color(value, window_bg))
    return None


def theme_to_css(theme, mode: str) -> str:
    mode_default = '#202020' if mode == 'dark' else '#F3F3F3'
    raw_bg = theme.styles.get('WindowBorderStyle', {}).get('Background', mode_default)
    if GRADIENT_MARKER.match(raw_bg):
        window_bg = mode_default
    else:
        window_bg = flatten_color(raw_bg, mode_default)
    declarations = {}
    for style_key, prop, selector, css_prop, kind in PROPERTY_MAP:
        value = theme.styles.get(style_key, {}).get(prop)
        if value is not None:
            rendered = transform(value, kind, window_bg)
            if rendered.startswith('linear-gradient') and css_prop == 'background-color':
                css_prop = 'background'
            declarations.setdefault(selector, {})[css_prop] = rendered
    for resource_key, selector, css_prop, kind in RESOURCE_MAP:
        value = theme.resources.get(resource_key)
        if value is not None:
            declarations.setdefault(selector, {})[css_prop] = transform(value, kind, window_bg)
    thumb_color = theme.resources.get('ThumbColor', FALLBACK_RESOURCES[mode]['ThumbColor'])
    declarations.setdefault('#ResultsScrollbar .thumb', {})['background-color'] = transform(thumb_color, 'color', window_bg)
    if 'background' not in declarations.get('#WindowBorder', {}):
        declarations.setdefault('#WindowBorder', {}).setdefault('background-color', window_bg)
    selected = selected_row_rule(theme, window_bg)
    if selected:
        declarations.setdefault(selected[0], {})[selected[1]] = selected[2]
    border_color = declarations.get('#WindowBorder', {}).pop('border-color', None)
    if border_color:
        declarations['#WindowBorder']['border'] = f"1px solid {border_color}"

    lines = []
    if theme.warnings:
        lines.append('/* warnings: ' + '; '.join(theme.warnings) + ' */')
    lines.append(f"/* Generated from {theme.metadata.get('Name', 'unknown')} ({mode}). */")
    lines.append(LAYOUT_SHEET.read_text())
    for selector, props in declarations.items():
        lines.append(f"{selector} {{")
        lines.extend(f"    {prop}: {value};" for prop, value in props.items())
        lines.append('}')
    return '\n'.join(lines) + '\n'
