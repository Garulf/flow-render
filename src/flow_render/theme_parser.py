from dataclasses import dataclass, field
import re
import xml.etree.ElementTree as ET

RESOURCE_TAGS = {'Color', 'SolidColorBrush', 'Double', 'String', 'Boolean',
                 'CornerRadius', 'Thickness'}
REFERENCE_PATTERN = re.compile(
    r'\{(?:(?:Static|Dynamic)Resource|m:DynamicColor)\s+(\S+?)\}')
BASED_ON_PATTERN = re.compile(r'\{StaticResource\s+(\S+?)\}')
HEADER_PATTERN = re.compile(r'<!--(.*?)-->', re.DOTALL)
HEADER_LINE_PATTERN = re.compile(r'^\s*(\w+):\s*(.+?)\s*$', re.MULTILINE)


@dataclass
class ThemeData:
    styles: dict = field(default_factory=dict)
    resources: dict = field(default_factory=dict)
    based_on: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def strip_namespace(tag: str) -> str:
    return tag.rsplit('}', 1)[-1]


def attribute(element, name: str):
    for key, value in element.attrib.items():
        if strip_namespace(key) == name:
            return value
    return None


def parse_header_metadata(text: str) -> dict:
    match = HEADER_PATTERN.search(text)
    if not match:
        return {}
    return dict(HEADER_LINE_PATTERN.findall(match.group(1)))


def parse_theme_xml(text: str) -> ThemeData:
    theme = ThemeData(metadata=parse_header_metadata(text))
    root = ET.fromstring(text)
    for element in root:
        tag = strip_namespace(element.tag)
        key = attribute(element, 'Key')
        if key is None:
            continue
        if tag == 'Style':
            theme.styles[key] = parse_setters(element)
            based_on = attribute(element, 'BasedOn')
            if based_on:
                match = BASED_ON_PATTERN.match(based_on)
                if match:
                    theme.based_on[key] = match.group(1)
        elif tag in RESOURCE_TAGS:
            value = attribute(element, 'Color') or (element.text or '').strip()
            theme.resources[key] = value
    return theme


def parse_setters(style_element) -> dict:
    setters = {}
    for child in style_element:
        if strip_namespace(child.tag) != 'Setter':
            continue
        prop = attribute(child, 'Property')
        value = attribute(child, 'Value')
        if value is None:
            value = parse_element_value(child)
        if prop and value is not None:
            setters[prop] = value
    return setters


def parse_element_value(setter_element):
    for brush in setter_element.iter():
        if strip_namespace(brush.tag) != 'LinearGradientBrush':
            continue
        stops = ';'.join(
            f"{attribute(stop, 'Color')}@{attribute(stop, 'Offset') or '0'}"
            for stop in brush.iter()
            if strip_namespace(stop.tag) == 'GradientStop')
        start = attribute(brush, 'StartPoint') or '0,0'
        end = attribute(brush, 'EndPoint') or '0,1'
        return f"{{Gradient {start}|{end}|{stops}}}"
    return None


FALLBACK_RESOURCES = {
    'light': {
        'Color01B': '#F3F3F3',
        'Color02B': '#E8E8E8',
        'Color03B': '#605E5C',
        'Color04B': '#605E5C',
        'Color05B': '#1B1B1B',
        'SubTitleForeground': '#605E5C',
        'SubTitleSelectedForeground': '#605E5C',
        'SeparatorForeground': '#E8E8E8',
        'QuerySuggestionBoxForeground': '#C3C3C3',
        'SearchIconForeground': '#1B1B1B',
        'NewHotkeyForeground': '#B3B3B3',
        'BasicHotkeyBGColor': '#E9E9E9',
        'ItemSelectedBackgroundColorBrush': '#F9F9F9',
        'ItemSelectedBackgroundColor': '#F9F9F9',
        'BasicSystemAccentColor': '#0078D4',
        'SystemAccentColorLight1Brush': '#0078D4',
        'SystemThemeBorder': '#4A4A4A',
        'ThumbColor': '#C0C0C0',
        'ClockDateForeground': '#605E5C',
        'QueryBoxSecondaryForeground': '#C3C3C3',
    },
    'dark': {
        'Color01B': '#202020',
        'Color02B': '#2D2D2D',
        'Color03B': '#A0A0A0',
        'Color04B': '#A0A0A0',
        'Color05B': '#FFFFFF',
        'SubTitleForeground': '#A0A0A0',
        'SubTitleSelectedForeground': '#A0A0A0',
        'SeparatorForeground': '#2D2D2D',
        'QuerySuggestionBoxForeground': '#6C6C6C',
        'SearchIconForeground': '#FFFFFF',
        'NewHotkeyForeground': '#8F8F8F',
        'BasicHotkeyBGColor': '#313131',
        'ItemSelectedBackgroundColorBrush': '#2B2B2B',
        'ItemSelectedBackgroundColor': '#2B2B2B',
        'BasicSystemAccentColor': '#0091F8',
        'SystemAccentColorLight1Brush': '#0091F8',
        'SystemThemeBorder': '#4A4A4A',
        'ThumbColor': '#454545',
        'ClockDateForeground': '#A0A0A0',
        'QueryBoxSecondaryForeground': '#6C6C6C',
    },
}

FALLBACK_BY_KIND = {
    'Foreground': 'Color05B',
    'Background': 'Color01B',
    'BorderBrush': 'SystemThemeBorder',
    'Fill': 'Color05B',
    'Stroke': 'BasicSystemAccentColor',
    'CaretBrush': 'Color05B',
    'SelectionBrush': 'BasicSystemAccentColor',
}


def resolve_theme(theme: ThemeData, base: ThemeData, mode: str) -> ThemeData:
    resolved = ThemeData(
        metadata=dict(theme.metadata),
        warnings=list(theme.warnings),
    )
    resolved.resources = {
        key: resolve_value(value, key, theme, base, mode, resolved.warnings)
        for key, value in theme.resources.items()
    }
    for key, setters in theme.styles.items():
        merged = dict(base.styles.get(theme.based_on.get(key, ''), {}))
        merged.update(setters)
        resolved.styles[key] = {
            prop: resolve_value(value, prop, theme, base, mode, resolved.warnings)
            for prop, value in merged.items()
        }
    return resolved


def resolve_value(value: str, prop: str, theme: ThemeData, base: ThemeData,
                  mode: str, warnings: list, seen: frozenset = frozenset()) -> str:
    match = REFERENCE_PATTERN.match(value.strip())
    if not match:
        return value
    name = match.group(1)
    if name not in seen:
        for source in (theme.resources, base.resources, FALLBACK_RESOURCES[mode]):
            if name in source:
                return resolve_value(source[name], prop, theme, base, mode,
                                     warnings, seen | {name})
    fallback_key = FALLBACK_BY_KIND.get(prop, 'Color05B')
    fallback = FALLBACK_RESOURCES[mode][fallback_key]
    warnings.append(f"unresolved resource '{name}' for {prop}; using {fallback}")
    return fallback
