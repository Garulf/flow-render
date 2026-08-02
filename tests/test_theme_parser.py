from web_render.theme_parser import parse_theme_xml

FIXTURE = """<!--
    Name: Test Theme
    IsDark: True
    HasBlur: False
-->
<ResourceDictionary
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
    xmlns:system="clr-namespace:System;assembly=mscorlib">
    <Color x:Key="AccentColor">#FF79C6</Color>
    <system:Double x:Key="ResultItemHeight">58</system:Double>
    <CornerRadius x:Key="ItemRadius">5</CornerRadius>
    <Style x:Key="QueryBoxStyle" BasedOn="{StaticResource BaseQueryBoxStyle}" TargetType="{x:Type TextBox}">
        <Setter Property="Foreground" Value="#f8f8f2" />
        <Setter Property="FontSize" Value="26" />
    </Style>
    <Style x:Key="ItemTitleStyle" TargetType="{x:Type TextBlock}">
        <Setter Property="Foreground" Value="{DynamicResource Color05B}" />
    </Style>
</ResourceDictionary>"""


def test_parses_style_setters():
    theme = parse_theme_xml(FIXTURE)

    assert theme.styles["QueryBoxStyle"]["Foreground"] == "#f8f8f2"
    assert theme.styles["QueryBoxStyle"]["FontSize"] == "26"


def test_parses_top_level_resources():
    theme = parse_theme_xml(FIXTURE)

    assert theme.resources["AccentColor"] == "#FF79C6"
    assert theme.resources["ResultItemHeight"] == "58"
    assert theme.resources["ItemRadius"] == "5"


def test_parses_based_on_references():
    theme = parse_theme_xml(FIXTURE)

    assert theme.based_on["QueryBoxStyle"] == "BaseQueryBoxStyle"


def test_parses_header_metadata_comment():
    theme = parse_theme_xml(FIXTURE)

    assert theme.metadata == {"Name": "Test Theme", "IsDark": "True", "HasBlur": "False"}


def test_keeps_raw_dynamic_resource_references():
    theme = parse_theme_xml(FIXTURE)

    assert theme.styles["ItemTitleStyle"]["Foreground"] == "{DynamicResource Color05B}"


GRADIENT_FIXTURE = """<ResourceDictionary
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <Style x:Key="WindowBorderStyle" TargetType="{x:Type Border}">
        <Setter Property="Background">
            <Setter.Value>
                <LinearGradientBrush StartPoint="0,0" EndPoint="0,1">
                    <GradientStop Color="#282a36" Offset="0" />
                    <GradientStop Color="#44475a" Offset="1" />
                </LinearGradientBrush>
            </Setter.Value>
        </Setter>
    </Style>
</ResourceDictionary>"""


def test_parses_gradient_setter_into_marker_string():
    theme = parse_theme_xml(GRADIENT_FIXTURE)

    assert theme.styles["WindowBorderStyle"]["Background"] == \
        "{Gradient 0,0|0,1|#282a36@0;#44475a@1}"


from web_render.theme_parser import FALLBACK_RESOURCES, resolve_theme

BASE_FIXTURE = """<ResourceDictionary
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <Style x:Key="BaseQueryBoxStyle" TargetType="{x:Type TextBox}">
        <Setter Property="Height" Value="42" />
        <Setter Property="FontSize" Value="16" />
    </Style>
</ResourceDictionary>"""


def resolved_fixture(mode="dark"):
    return resolve_theme(parse_theme_xml(FIXTURE), parse_theme_xml(BASE_FIXTURE), mode)


def test_based_on_merges_base_setters_under_theme_setters():
    theme = resolved_fixture()

    assert theme.styles["QueryBoxStyle"]["Height"] == "42"
    assert theme.styles["QueryBoxStyle"]["FontSize"] == "26"


def test_static_resource_resolves_from_theme_resources():
    source = FIXTURE.replace('Value="#f8f8f2"', 'Value="{StaticResource AccentColor}"')
    theme = resolve_theme(parse_theme_xml(source), parse_theme_xml(BASE_FIXTURE), "dark")

    assert theme.styles["QueryBoxStyle"]["Foreground"] == "#FF79C6"


def test_dynamic_resource_falls_back_to_mode_table():
    theme = resolved_fixture(mode="dark")

    assert theme.styles["ItemTitleStyle"]["Foreground"] == FALLBACK_RESOURCES["dark"]["Color05B"]
    assert FALLBACK_RESOURCES["dark"]["Color05B"] == "#FFFFFF"
    assert FALLBACK_RESOURCES["light"]["Color05B"] == "#1B1B1B"


def test_unknown_reference_uses_property_kind_fallback_and_warns():
    source = FIXTURE.replace(
        '{DynamicResource Color05B}', '{DynamicResource NoSuchResourceXyz}')
    theme = resolve_theme(parse_theme_xml(source), parse_theme_xml(BASE_FIXTURE), "dark")

    assert theme.styles["ItemTitleStyle"]["Foreground"] == FALLBACK_RESOURCES["dark"]["Color05B"]
    assert any("NoSuchResourceXyz" in warning for warning in theme.warnings)


def test_m_dynamic_color_resources_resolve_via_fallback_table():
    source = FIXTURE.replace(
        '<Color x:Key="AccentColor">#FF79C6</Color>',
        '<SolidColorBrush x:Key="ItemSelectedBackgroundColor" '
        'Color="{m:DynamicColor ItemSelectedBackgroundColorBrush}" />')
    theme = resolve_theme(parse_theme_xml(source), parse_theme_xml(BASE_FIXTURE), "dark")

    assert theme.resources["ItemSelectedBackgroundColor"] == "#2B2B2B"
