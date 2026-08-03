from web_render.edit_state import (
    Transform, GradientStop, GradientState, TextLayer, EditState,
    edit_state_to_css, edit_state_to_dict, apply_update,
)


def test_transform_default_has_no_translate_or_rotate():
    assert Transform().is_default()


def test_transform_is_not_default_when_any_field_set():
    assert not Transform(translate_x=10).is_default()
    assert not Transform(rotate_z=90).is_default()


def test_transform_is_not_default_when_perspective_is_nonzero():
    assert not Transform(perspective=2000).is_default()


def test_transform_is_default_when_perspective_is_zero():
    assert Transform(perspective=0).is_default()


def test_transform_is_not_default_when_scale_is_not_one():
    assert not Transform(scale=1.5).is_default()


def test_transform_to_css_value():
    transform = Transform(translate_x=10, translate_y=-5, translate_z=0,
                          rotate_x=0, rotate_y=45, rotate_z=0)

    assert transform.to_css_value() == (
        "translate3d(10px, -5px, 0px) rotateX(0deg) rotateY(45deg) rotateZ(0deg) scale(1)"
    )


def test_transform_to_css_value_prefixes_perspective_with_its_distance():
    transform = Transform(rotate_x=45, rotate_y=-45, perspective=800)

    assert transform.to_css_value() == (
        "perspective(800px) translate3d(0px, 0px, 0px) "
        "rotateX(45deg) rotateY(-45deg) rotateZ(0deg) scale(1)"
    )


def test_transform_to_css_value_composes_with_a_preserve_prefix():
    transform = Transform(translate_z=100)

    assert transform.to_css_value("translateY(-50%)") == (
        "translateY(-50%) translate3d(0px, 0px, 100px) "
        "rotateX(0deg) rotateY(0deg) rotateZ(0deg) scale(1)"
    )


def test_transform_to_css_value_includes_scale():
    transform = Transform(scale=1.3)

    assert transform.to_css_value() == (
        "translate3d(0px, 0px, 0px) rotateX(0deg) rotateY(0deg) rotateZ(0deg) scale(1.3)"
    )


def test_gradient_to_css_value():
    gradient = GradientState(angle=90, stops=[
        GradientStop(color="#000000", position=0),
        GradientStop(color="#ffffff", position=100),
    ])

    assert gradient.to_css_value() == "linear-gradient(90deg, #000000 0%, #ffffff 100%)"


def test_edit_state_to_css_is_empty_for_a_blank_state():
    state = EditState()

    assert edit_state_to_css(state) == ""


def test_edit_state_to_css_emits_canvas_gradient():
    state = EditState(canvas=GradientState(angle=180, stops=[
        GradientStop(color="#1a1a2e", position=0),
        GradientStop(color="#16213e", position=100),
    ]))

    css = edit_state_to_css(state)

    assert "html, body {" in css
    assert "background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);" in css


def test_edit_state_to_css_omits_default_element_transforms():
    state = EditState(elements={"#WindowBorder": Transform()})

    assert edit_state_to_css(state) == ""


def test_edit_state_to_css_emits_non_default_element_transform():
    state = EditState(elements={"#WindowBorder": Transform(translate_x=10, rotate_y=45)})

    css = edit_state_to_css(state)

    assert "#WindowBorder {" in css
    assert "transform: translate3d(10px, 0px, 0px) rotateX(0deg) rotateY(45deg) rotateZ(0deg) scale(1);" in css


def test_edit_state_to_css_preserves_icon_centering_transform():
    state = EditState(elements={".icon": Transform(translate_z=100)})

    css = edit_state_to_css(state)

    assert "transform: translateY(-50%) translate3d(0px, 0px, 100px)" in css


def test_edit_state_to_css_preserves_glass_icon_and_hotkey_centering_transform():
    state = EditState(elements={
        "#GlassIcon": Transform(translate_x=10),
        ".Hotkey": Transform(translate_x=-10),
    })

    css = edit_state_to_css(state)

    assert "transform: translateY(-50%) translate3d(10px, 0px, 0px)" in css
    assert "transform: translateY(-50%) translate3d(-10px, 0px, 0px)" in css


def test_edit_state_to_css_does_not_add_preserve_prefix_for_window_border():
    state = EditState(elements={"#WindowBorder": Transform(rotate_x=45)})

    css = edit_state_to_css(state)

    assert "transform: translate3d(0px, 0px, 0px) rotateX(45deg)" in css
    assert "translateY(-50%)" not in css


def test_edit_state_to_css_emits_non_default_scale():
    state = EditState(elements={"#WindowBorder": Transform(scale=1.3)})

    css = edit_state_to_css(state)

    assert "scale(1.3)" in css


def test_transform_is_not_default_when_opacity_is_not_one():
    assert not Transform(opacity=0.5).is_default()


def test_transform_is_not_default_when_shadow_opacity_is_nonzero():
    assert not Transform(shadow_opacity=0.5).is_default()


def test_transform_extra_declarations_empty_by_default():
    assert Transform().extra_declarations() == []


def test_transform_extra_declarations_includes_opacity_when_not_one():
    assert Transform(opacity=0.5).extra_declarations() == ["opacity: 0.5;"]


def test_transform_extra_declarations_includes_drop_shadow_when_shadow_opacity_set():
    transform = Transform(shadow_x=4, shadow_y=8, shadow_blur=12,
                          shadow_color="#ff0000", shadow_opacity=0.6)

    declarations = transform.extra_declarations()

    assert declarations == ["filter: drop-shadow(4px 8px 12px rgba(255, 0, 0, 0.6));"]


def test_edit_state_to_css_emits_opacity_and_shadow_for_an_element():
    state = EditState(elements={
        ".icon": Transform(opacity=0.7, shadow_x=2, shadow_y=2, shadow_blur=4,
                           shadow_color="#000000", shadow_opacity=0.5),
    })

    css = edit_state_to_css(state)

    assert "opacity: 0.7;" in css
    assert "filter: drop-shadow(2px 2px 4px rgba(0, 0, 0, 0.5));" in css


def test_edit_state_to_css_emits_shadow_for_a_layer():
    state = EditState(layers=[
        TextLayer(active=True, template="hi",
                 transform=Transform(shadow_x=1, shadow_y=1, shadow_blur=2,
                                     shadow_color="#333333", shadow_opacity=0.8)),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)

    assert "filter: drop-shadow(1px 1px 2px rgba(51, 51, 51, 0.8));" in css


def test_edit_state_to_css_emits_layer_font_family():
    state = EditState(layers=[
        TextLayer(active=True, template="hi", font_family="Georgia, serif"),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)

    assert "font-family: Georgia, serif;" in css


def test_edit_state_to_css_emits_layer_color_with_alpha_when_not_opaque():
    state = EditState(layers=[
        TextLayer(active=True, template="hi", color="#ff0000", color_opacity=0.4),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)

    assert "color: rgba(255, 0, 0, 0.4);" in css


def test_edit_state_to_css_emits_plain_layer_color_when_fully_opaque():
    state = EditState(layers=[
        TextLayer(active=True, template="hi", color="#ff0000", color_opacity=1),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)

    assert "color: #ff0000;" in css


def test_gradient_to_css_value_supports_radial():
    gradient = GradientState(gradient_type="radial", stops=[
        GradientStop(color="#000000", position=0),
        GradientStop(color="#ffffff", position=100),
    ])

    assert gradient.to_css_value() == "radial-gradient(#000000 0%, #ffffff 100%)"


def test_gradient_to_css_value_supports_more_than_two_stops():
    gradient = GradientState(angle=90, stops=[
        GradientStop(color="#000000", position=0),
        GradientStop(color="#ff0000", position=50),
        GradientStop(color="#ffffff", position=100),
    ])

    assert gradient.to_css_value() == "linear-gradient(90deg, #000000 0%, #ff0000 50%, #ffffff 100%)"


def test_edit_state_to_css_unclips_window_when_an_inner_element_is_transformed():
    state = EditState(elements={".icon": Transform(translate_z=100)})

    css = edit_state_to_css(state)

    assert "#WindowBorder {\n    overflow: visible;\n}" in css


def test_edit_state_to_css_does_not_unclip_window_for_the_windows_own_transform():
    state = EditState(elements={"#WindowBorder": Transform(rotate_x=45, perspective=2000)})

    css = edit_state_to_css(state)

    assert "overflow: visible" not in css


def test_edit_state_to_css_does_not_unclip_window_with_no_transformed_elements():
    state = EditState()

    assert "overflow: visible" not in edit_state_to_css(state)


def test_edit_state_to_css_omits_inactive_layers():
    state = EditState(layers=[TextLayer(), TextLayer(), TextLayer(), TextLayer()])

    assert edit_state_to_css(state) == ""


def test_edit_state_to_css_emits_transparent_canvas():
    state = EditState(transparent=True)

    css = edit_state_to_css(state)

    assert "html, body {" in css
    assert "background: transparent;" in css


def test_edit_state_to_css_transparent_takes_precedence_over_gradient():
    state = EditState(transparent=True, canvas=GradientState(stops=[
        GradientStop(color="#000", position=0),
        GradientStop(color="#fff", position=100),
    ]))

    css = edit_state_to_css(state)

    assert "background: transparent;" in css
    assert "linear-gradient" not in css


def test_edit_state_to_css_emits_active_layer_with_live_jinja_template():
    state = EditState(layers=[
        TextLayer(active=True, template="{{ plugin.Name }}", font_size=40, color="#fff", weight="bold"),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)

    assert "#Layer1 {" in css
    assert "display: block;" in css
    assert '#Layer1::before {' in css
    assert 'content: "{{ plugin.Name }}";' in css
    assert "font-size: 40px;" in css
    assert "color: #fff;" in css
    assert "font-weight: bold;" in css


def test_edit_state_to_css_puts_layer_font_styles_on_host_not_pseudo_element():
    state = EditState(layers=[
        TextLayer(active=True, template="hi", font_size=40, color="#fff", weight="bold"),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)
    host_block = css.split("#Layer1 {", 1)[1].split("}", 1)[0]
    before_block = css.split("#Layer1::before {", 1)[1].split("}", 1)[0]

    assert "font-size: 40px;" in host_block
    assert "color: #fff;" in host_block
    assert "font-weight: bold;" in host_block
    assert "font-size" not in before_block
    assert "color" not in before_block
    assert "font-weight" not in before_block


def test_edit_state_to_css_escapes_quotes_in_template_text():
    state = EditState(layers=[
        TextLayer(active=True, template='Say "hi" {{ plugin.Name }}'),
        TextLayer(), TextLayer(), TextLayer(),
    ])

    css = edit_state_to_css(state)

    assert 'content: "Say \\"hi\\" {{ plugin.Name }}";' in css


def test_edit_state_to_css_prefixes_include_when_base_css_files_given():
    state = EditState(base_css_files=["ad-neon.css"],
                      canvas=GradientState(stops=[
                          GradientStop(color="#000", position=0),
                          GradientStop(color="#fff", position=100),
                      ]))

    css = edit_state_to_css(state)

    assert css.startswith("{% include 'ad-neon.css' %}\n")


def test_edit_state_to_css_omits_canvas_size_marker_at_default_size():
    state = EditState()

    assert "web-render-canvas" not in edit_state_to_css(state)


def test_edit_state_to_css_emits_canvas_size_marker_when_non_default():
    state = EditState(canvas_width=1600, canvas_height=900)

    css = edit_state_to_css(state)

    assert "/* web-render-canvas: 1600x900 */" in css


def test_edit_state_to_dict_round_trips_canvas_and_elements_and_layers():
    state = EditState(
        canvas=GradientState(angle=45, stops=[GradientStop(color="#000", position=0)]),
        elements={"#WindowBorder": Transform(translate_x=5)},
        layers=[TextLayer(active=True, template="hi"), TextLayer(), TextLayer(), TextLayer()],
    )

    data = edit_state_to_dict(state)

    assert data["canvas"]["angle"] == 45
    assert data["elements"]["#WindowBorder"]["translate_x"] == 5
    assert data["layers"][0]["active"] is True
    assert data["layers"][0]["template"] == "hi"
    assert data["layers"][1]["active"] is False
    assert "base_css_files" not in data


def test_edit_state_to_dict_includes_transparent_and_canvas_size():
    state = EditState(transparent=True, canvas_width=1600, canvas_height=900)

    data = edit_state_to_dict(state)

    assert data["transparent"] is True
    assert data["canvas_width"] == 1600
    assert data["canvas_height"] == 900


def test_apply_update_sets_canvas():
    state = EditState()

    apply_update(state, {
        "type": "canvas",
        "canvas": {"angle": 90, "stops": [{"color": "#000", "position": 0}, {"color": "#fff", "position": 100}]},
    })

    assert state.canvas.angle == 90
    assert state.canvas.stops[0].color == "#000"
    assert state.transparent is False


def test_apply_update_canvas_clears_gradient_when_transparent_enabled():
    state = EditState(canvas=GradientState(stops=[GradientStop(color="#000", position=0)]))

    apply_update(state, {"type": "canvas", "canvas": None, "transparent": True})

    assert state.canvas is None
    assert state.transparent is True


def test_apply_update_sets_canvas_size():
    state = EditState()

    apply_update(state, {"type": "canvas_size", "width": 1600, "height": 900})

    assert state.canvas_width == 1600
    assert state.canvas_height == 900


def test_apply_update_sets_element_transform_with_perspective():
    state = EditState()

    apply_update(state, {
        "type": "element",
        "selector": "#WindowBorder",
        "transform": {"translate_x": 0, "translate_y": 0, "translate_z": 0,
                      "rotate_x": 45, "rotate_y": -45, "rotate_z": 0, "perspective": 1200},
    })

    assert state.elements["#WindowBorder"].perspective == 1200


def test_apply_update_sets_element_transform():
    state = EditState()

    apply_update(state, {
        "type": "element",
        "selector": "#WindowBorder",
        "transform": {"translate_x": 10, "translate_y": 0, "translate_z": 0,
                      "rotate_x": 0, "rotate_y": 0, "rotate_z": 0},
    })

    assert state.elements["#WindowBorder"].translate_x == 10


def test_apply_update_sets_layer():
    state = EditState()

    apply_update(state, {
        "type": "layer",
        "slot": 0,
        "layer": {"active": True, "template": "{{ plugin.Name }}", "font_size": 40,
                  "color": "#fff", "weight": "bold",
                  "transform": {"translate_x": 0, "translate_y": 0, "translate_z": 0,
                                "rotate_x": 0, "rotate_y": 0, "rotate_z": 0}},
    })

    assert state.layers[0].active is True
    assert state.layers[0].template == "{{ plugin.Name }}"


def test_apply_update_raises_on_unknown_type():
    state = EditState()

    try:
        apply_update(state, {"type": "bogus"})
        assert False, "expected ValueError"
    except ValueError:
        pass
