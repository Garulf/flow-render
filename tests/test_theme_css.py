import pytest

from web_render.theme_css import flatten_color, gradient_to_css, radius_to_css, thickness_to_css


@pytest.mark.parametrize("wpf, css", [
    ("10 0 10 0", "0 10px 0 10px"),
    ("4 8", "8px 4px"),
    ("6", "6px"),
    ("0 10 0 10", "10px 0 10px 0"),
])
def test_thickness_reorders_wpf_to_css(wpf, css):
    assert thickness_to_css(wpf) == css


def test_flatten_color_composites_argb_over_background():
    assert flatten_color("#D6202020", "#202020") == "#202020"
    assert flatten_color("#80000000", "#FFFFFF") == "#7F7F7F"


def test_flatten_color_passes_through_opaque_and_named():
    assert flatten_color("#f8f8f2", "#000000") == "#f8f8f2"
    assert flatten_color("Transparent", "#202020") == "#202020"
    assert flatten_color("White", "#000000") == "#FFFFFF"


def test_radius_handles_uniform_and_per_corner():
    assert radius_to_css("5") == "5px"
    assert radius_to_css("8,8,0,0") == "8px 8px 0px 0px"


def test_gradient_produces_css_linear_gradient():
    css = gradient_to_css("0,0", "0,1", [("#282a36", 0.0), ("#44475a", 1.0)])
    assert css == "linear-gradient(180deg, #282a36 0%, #44475a 100%)"


from pathlib import Path

LAYOUT_PATH = Path(__file__).parent.parent / 'src' / 'web_render' / 'theme_layout.css'


def test_layout_sheet_is_structural_only():
    content = LAYOUT_PATH.read_text()

    assert '#WindowBorder' in content
    assert '.selecteditem::before' in content
    assert 'color:' not in content
    assert 'background-color: #' not in content


from web_render.theme_parser import ThemeData
from web_render.theme_css import theme_to_css


def make_resolved_theme():
    return ThemeData(
        styles={
            "WindowBorderStyle": {"Background": "#282a36", "BorderBrush": "#44475a",
                                  "BorderThickness": "1"},
            "QueryBoxStyle": {"Foreground": "#f8f8f2", "FontSize": "26",
                              "Height": "42", "CaretBrush": "#f8f8f2"},
            "QuerySuggestionBoxStyle": {"Foreground": "#6272a4"},
            "ItemTitleStyle": {"Foreground": "#f8f8f2", "FontSize": "16"},
            "ItemSubTitleStyle": {"Foreground": "#6272a4", "FontSize": "13"},
            "ItemTitleSelectedStyle": {"Foreground": "#ff79c6"},
            "ItemBulletSelectedStyle": {"Width": "4", "Height": "38",
                                        "CornerRadius": "2", "Background": "#ff79c6"},
            "SeparatorStyle": {"Fill": "#44475a", "Height": "1"},
            "ItemHotkeyStyle": {"Foreground": "#6272a4", "FontSize": "13"},
            "ItemHotkeyBGStyle": {"Background": "#21222c"},
        },
        resources={"ItemRadius": "5", "ResultItemHeight": "58"},
        metadata={"Name": "Dracula", "IsDark": "True"},
        warnings=["unresolved resource 'X' for Fill; using #FFFFFF"],
    )


def test_emits_window_and_text_rules():
    css = theme_to_css(make_resolved_theme(), "dark")

    assert "#WindowBorder {" in css
    assert "background-color: #282a36;" in css
    assert "border: 1px solid #44475a;" in css
    assert "#QueryBoxText {" in css and "font-size: 26px;" in css
    assert ".selecteditem .Title {\n    color: #ff79c6;" in css


def test_emits_bullet_and_metrics():
    css = theme_to_css(make_resolved_theme(), "dark")

    assert ".selecteditem::before" in css
    assert "background-color: #ff79c6;" in css
    item_block = css.rsplit(".item {", 1)[1].split("}", 1)[0]
    assert "height: 58px;" in item_block
    assert "border-radius: 5px;" in item_block


def test_output_is_self_contained_and_carries_warnings():
    css = theme_to_css(make_resolved_theme(), "dark")

    assert ".item-text-container" in css
    assert css.index(".item-text-container") < css.index("#WindowBorder {\n    background-color")
    assert "unresolved" in css[:400]
