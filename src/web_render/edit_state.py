from dataclasses import dataclass, field, asdict
from typing import Optional

LAYER_SELECTORS = ["#Layer1", "#Layer2", "#Layer3", "#Layer4"]
LAYER_COUNT = len(LAYER_SELECTORS)


@dataclass
class Transform:
    translate_x: float = 0
    translate_y: float = 0
    translate_z: float = 0
    rotate_x: float = 0
    rotate_y: float = 0
    rotate_z: float = 0

    def is_default(self) -> bool:
        return not any([
            self.translate_x, self.translate_y, self.translate_z,
            self.rotate_x, self.rotate_y, self.rotate_z,
        ])

    def to_css_value(self) -> str:
        return (
            f"translate3d({self.translate_x}px, {self.translate_y}px, {self.translate_z}px) "
            f"rotateX({self.rotate_x}deg) rotateY({self.rotate_y}deg) rotateZ({self.rotate_z}deg)"
        )


@dataclass
class GradientStop:
    color: str
    position: float


@dataclass
class GradientState:
    angle: float = 180
    stops: list = field(default_factory=list)

    def to_css_value(self) -> str:
        stops = ", ".join(f"{stop.color} {stop.position}%" for stop in self.stops)
        return f"linear-gradient({self.angle}deg, {stops})"


@dataclass
class TextLayer:
    active: bool = False
    template: str = ""
    transform: Transform = field(default_factory=Transform)
    font_size: int = 32
    color: str = "#ffffff"
    weight: str = "normal"


@dataclass
class EditState:
    base_css_files: list = field(default_factory=list)
    canvas: Optional[GradientState] = None
    elements: dict = field(default_factory=dict)
    layers: list = field(default_factory=lambda: [TextLayer() for _ in range(LAYER_COUNT)])


def _escape_css_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def edit_state_to_css(state: EditState) -> str:
    lines = []
    for base_file in state.base_css_files:
        lines.append(f"{{% include '{base_file}' %}}")

    if state.canvas is not None and state.canvas.stops:
        lines.append("html, body {")
        lines.append(f"    background: {state.canvas.to_css_value()};")
        lines.append("}")

    if any(layer.active for layer in state.layers):
        lines.append("#WindowBorder {")
        lines.append("    overflow: visible;")
        lines.append("}")

    for selector, transform in state.elements.items():
        if transform.is_default():
            continue
        lines.append(f"{selector} {{")
        lines.append(f"    transform: {transform.to_css_value()};")
        lines.append("}")

    for slot_index, layer in enumerate(state.layers):
        if not layer.active:
            continue
        selector = LAYER_SELECTORS[slot_index]
        lines.append(f"{selector} {{")
        lines.append("    display: block;")
        if not layer.transform.is_default():
            lines.append(f"    transform: {layer.transform.to_css_value()};")
        lines.append("}")
        lines.append(f"{selector}::before {{")
        lines.append(f'    content: "{_escape_css_string(layer.template)}";')
        lines.append(f"    font-size: {layer.font_size}px;")
        lines.append(f"    color: {layer.color};")
        lines.append(f"    font-weight: {layer.weight};")
        lines.append("}")

    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def edit_state_to_dict(state: EditState) -> dict:
    return {
        "canvas": asdict(state.canvas) if state.canvas else None,
        "elements": {selector: asdict(transform) for selector, transform in state.elements.items()},
        "layers": [asdict(layer) for layer in state.layers],
    }


def transform_from_dict(data: dict) -> Transform:
    return Transform(
        translate_x=data.get("translate_x", 0),
        translate_y=data.get("translate_y", 0),
        translate_z=data.get("translate_z", 0),
        rotate_x=data.get("rotate_x", 0),
        rotate_y=data.get("rotate_y", 0),
        rotate_z=data.get("rotate_z", 0),
    )


def gradient_from_dict(data: Optional[dict]) -> Optional[GradientState]:
    if data is None:
        return None
    return GradientState(
        angle=data.get("angle", 180),
        stops=[GradientStop(color=stop["color"], position=stop["position"])
               for stop in data.get("stops", [])],
    )


def text_layer_from_dict(data: dict) -> TextLayer:
    return TextLayer(
        active=data.get("active", False),
        template=data.get("template", ""),
        transform=transform_from_dict(data.get("transform", {})),
        font_size=data.get("font_size", 32),
        color=data.get("color", "#ffffff"),
        weight=data.get("weight", "normal"),
    )


def apply_update(state: EditState, update: dict) -> None:
    kind = update["type"]
    if kind == "canvas":
        state.canvas = gradient_from_dict(update["canvas"])
    elif kind == "element":
        state.elements[update["selector"]] = transform_from_dict(update["transform"])
    elif kind == "layer":
        state.layers[update["slot"]] = text_layer_from_dict(update["layer"])
    else:
        raise ValueError(f"Unknown update type: {kind}")
