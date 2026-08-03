from dataclasses import dataclass, field, asdict
from typing import Optional

LAYER_SELECTORS = ["#Layer1", "#Layer2", "#Layer3", "#Layer4"]
LAYER_COUNT = len(LAYER_SELECTORS)
DEFAULT_CANVAS_WIDTH = 1280
DEFAULT_CANVAS_HEIGHT = 720

# These selectors rely on `transform: translateY(-50%)` in every bundled theme for
# their own vertical centering. An edit-mode transform must be composed with that
# base transform (not replace it), or the element visibly jumps out of its centered
# position the moment any transform is applied to it.
TRANSFORM_PRESERVE_PREFIX = {
    "#GlassIcon": "translateY(-50%)",
    ".icon": "translateY(-50%)",
    ".Hotkey": "translateY(-50%)",
}


def _hex_to_rgba(hex_color: str, opacity: float) -> str:
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    r, g, b = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {opacity})"


@dataclass
class Transform:
    translate_x: float = 0
    translate_y: float = 0
    translate_z: float = 0
    rotate_x: float = 0
    rotate_y: float = 0
    rotate_z: float = 0
    scale: float = 1
    perspective: float = 0
    opacity: float = 1
    shadow_x: float = 0
    shadow_y: float = 0
    shadow_blur: float = 0
    shadow_color: str = "#000000"
    shadow_opacity: float = 0

    def is_default(self) -> bool:
        return not any([
            self.translate_x, self.translate_y, self.translate_z,
            self.rotate_x, self.rotate_y, self.rotate_z,
            self.perspective, self.shadow_opacity,
        ]) and self.scale == 1 and self.opacity == 1

    def to_css_value(self, preserve_prefix: str = "") -> str:
        perspective_prefix = f"perspective({self.perspective}px) " if self.perspective else ""
        preserve = f"{preserve_prefix} " if preserve_prefix else ""
        return (
            f"{preserve}{perspective_prefix}translate3d({self.translate_x}px, {self.translate_y}px, {self.translate_z}px) "
            f"rotateX({self.rotate_x}deg) rotateY({self.rotate_y}deg) rotateZ({self.rotate_z}deg) "
            f"scale({self.scale})"
        )

    def extra_declarations(self) -> list:
        """CSS declarations beyond `transform:` — kept separate since opacity and
        filter are their own properties, not part of the transform value."""
        lines = []
        if self.opacity != 1:
            lines.append(f"opacity: {self.opacity};")
        if self.shadow_opacity:
            color = _hex_to_rgba(self.shadow_color, self.shadow_opacity)
            lines.append(f"filter: drop-shadow({self.shadow_x}px {self.shadow_y}px {self.shadow_blur}px {color});")
        return lines


@dataclass
class GradientStop:
    color: str
    position: float
    opacity: float = 1

    def to_css_color(self) -> str:
        if self.opacity == 1:
            return self.color
        return _hex_to_rgba(self.color, self.opacity)


@dataclass
class GradientState:
    angle: float = 180
    gradient_type: str = "linear"
    center_x: float = 50
    center_y: float = 50
    stops: list = field(default_factory=list)

    def to_css_value(self) -> str:
        stops = ", ".join(f"{stop.to_css_color()} {stop.position}%" for stop in self.stops)
        if self.gradient_type == "radial":
            return f"radial-gradient(circle at {self.center_x}% {self.center_y}%, {stops})"
        return f"linear-gradient({self.angle}deg, {stops})"


@dataclass
class TextLayer:
    active: bool = False
    template: str = ""
    transform: Transform = field(default_factory=Transform)
    font_size: int = 32
    font_family: str = "inherit"
    color: str = "#ffffff"
    color_opacity: float = 1
    weight: str = "normal"


@dataclass
class EditState:
    base_css_files: list = field(default_factory=list)
    canvas: Optional[GradientState] = None
    transparent: bool = False
    canvas_width: int = DEFAULT_CANVAS_WIDTH
    canvas_height: int = DEFAULT_CANVAS_HEIGHT
    elements: dict = field(default_factory=dict)
    layers: list = field(default_factory=lambda: [TextLayer() for _ in range(LAYER_COUNT)])
    window_shine: Optional[GradientState] = None


def _escape_css_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def edit_state_to_css(state: EditState) -> str:
    lines = []
    for base_file in state.base_css_files:
        lines.append(f"{{% include '{base_file}' %}}")

    if (state.canvas_width, state.canvas_height) != (DEFAULT_CANVAS_WIDTH, DEFAULT_CANVAS_HEIGHT):
        lines.append(f"/* web-render-canvas: {state.canvas_width}x{state.canvas_height} */")

    if state.transparent:
        lines.append("html, body {")
        lines.append("    background: transparent;")
        lines.append("}")
    elif state.canvas is not None and state.canvas.stops:
        lines.append("html, body {")
        lines.append(f"    background: {state.canvas.to_css_value()};")
        lines.append("}")

    # A gradient overlay painted on top of the window's own content — typically a
    # soft, mostly-transparent band used to fake a glossy/shine highlight. It's a
    # dedicated element (not the window's own background) so it can use
    # transparent stops without hiding the theme underneath.
    if state.window_shine is not None and state.window_shine.stops:
        lines.append("#WindowShine {")
        lines.append("    display: block;")
        lines.append(f"    background: {state.window_shine.to_css_value()};")
        lines.append("}")

    # An element inside #WindowBorder (anything but the window itself) with a
    # non-default transform should be able to visually extend past the
    # window's edges (e.g. translateZ "popping" an icon out) rather than
    # being clipped by the window's own overflow: hidden.
    if any(not transform.is_default() for selector, transform in state.elements.items()
           if selector != "#WindowBorder"):
        lines.append("#WindowBorder {")
        lines.append("    overflow: visible;")
        lines.append("}")

    for selector, transform in state.elements.items():
        if transform.is_default():
            continue
        preserve_prefix = TRANSFORM_PRESERVE_PREFIX.get(selector, "")
        lines.append(f"{selector} {{")
        lines.append(f"    transform: {transform.to_css_value(preserve_prefix)};")
        for declaration in transform.extra_declarations():
            lines.append(f"    {declaration}")
        lines.append("}")

    for slot_index, layer in enumerate(state.layers):
        if not layer.active:
            continue
        selector = LAYER_SELECTORS[slot_index]
        lines.append(f"{selector} {{")
        lines.append("    display: block;")
        if not layer.transform.is_default():
            lines.append(f"    transform: {layer.transform.to_css_value()};")
            for declaration in layer.transform.extra_declarations():
                lines.append(f"    {declaration}")
        # font-size/family/color/font-weight live on the host element (not
        # ::before) so they're inherited by the pseudo-element's text content —
        # this lets a JS client restyle them by setting the host's inline
        # style, with no need to re-render the page for a font/color tweak.
        lines.append(f"    font-size: {layer.font_size}px;")
        lines.append(f"    font-family: {layer.font_family};")
        color = (_hex_to_rgba(layer.color, layer.color_opacity)
                if layer.color_opacity != 1 else layer.color)
        lines.append(f"    color: {color};")
        lines.append(f"    font-weight: {layer.weight};")
        lines.append("}")
        lines.append(f"{selector}::before {{")
        lines.append(f'    content: "{_escape_css_string(layer.template)}";')
        lines.append("}")

    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def edit_state_to_dict(state: EditState) -> dict:
    return {
        "canvas": asdict(state.canvas) if state.canvas else None,
        "transparent": state.transparent,
        "canvas_width": state.canvas_width,
        "canvas_height": state.canvas_height,
        "elements": {selector: asdict(transform) for selector, transform in state.elements.items()},
        "layers": [asdict(layer) for layer in state.layers],
        "window_shine": asdict(state.window_shine) if state.window_shine else None,
    }


def transform_from_dict(data: dict) -> Transform:
    return Transform(
        translate_x=data.get("translate_x", 0),
        translate_y=data.get("translate_y", 0),
        translate_z=data.get("translate_z", 0),
        rotate_x=data.get("rotate_x", 0),
        rotate_y=data.get("rotate_y", 0),
        rotate_z=data.get("rotate_z", 0),
        scale=data.get("scale", 1),
        perspective=data.get("perspective", 0),
        opacity=data.get("opacity", 1),
        shadow_x=data.get("shadow_x", 0),
        shadow_y=data.get("shadow_y", 0),
        shadow_blur=data.get("shadow_blur", 0),
        shadow_color=data.get("shadow_color", "#000000"),
        shadow_opacity=data.get("shadow_opacity", 0),
    )


def gradient_from_dict(data: Optional[dict]) -> Optional[GradientState]:
    if data is None:
        return None
    return GradientState(
        angle=data.get("angle", 180),
        gradient_type=data.get("gradient_type", "linear"),
        center_x=data.get("center_x", 50),
        center_y=data.get("center_y", 50),
        stops=[GradientStop(color=stop["color"], position=stop["position"], opacity=stop.get("opacity", 1))
               for stop in data.get("stops", [])],
    )


def text_layer_from_dict(data: dict) -> TextLayer:
    return TextLayer(
        active=data.get("active", False),
        template=data.get("template", ""),
        transform=transform_from_dict(data.get("transform", {})),
        font_size=data.get("font_size", 32),
        font_family=data.get("font_family", "inherit"),
        color=data.get("color", "#ffffff"),
        color_opacity=data.get("color_opacity", 1),
        weight=data.get("weight", "normal"),
    )


def apply_update(state: EditState, update: dict) -> None:
    kind = update["type"]
    if kind == "canvas":
        state.canvas = gradient_from_dict(update.get("canvas"))
        state.transparent = update.get("transparent", False)
    elif kind == "canvas_size":
        state.canvas_width = update["width"]
        state.canvas_height = update["height"]
    elif kind == "element":
        state.elements[update["selector"]] = transform_from_dict(update["transform"])
    elif kind == "layer":
        state.layers[int(update["slot"])] = text_layer_from_dict(update["layer"])
    elif kind == "window_shine":
        state.window_shine = gradient_from_dict(update.get("window_shine"))
    else:
        raise ValueError(f"Unknown update type: {kind}")
