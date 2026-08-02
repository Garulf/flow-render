from web_render.convert_themes import convert_file, slugify
from web_render.theme_parser import ThemeData

DRACULA_MINIMAL = """<!--
    Name: Dracula
    IsDark: True
-->
<ResourceDictionary
    xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
    <Style x:Key="WindowBorderStyle" TargetType="{x:Type Border}">
        <Setter Property="Background" Value="#282a36" />
    </Style>
</ResourceDictionary>"""

AUTO_MINIMAL = DRACULA_MINIMAL.replace("Dracula", "Circle System").replace(
    "</ResourceDictionary>",
    '<system:String xmlns:system="clr-namespace:System;assembly=mscorlib" '
    'x:Key="SystemBG">Auto</system:String></ResourceDictionary>')


def test_slugify():
    assert slugify("Nord Darker.xaml") == "nord-darker"
    assert slugify("BlurBlack Darker.xaml") == "blurblack-darker"


def test_convert_file_writes_one_css_for_single_mode(tmp_path):
    xaml = tmp_path / "Dracula.xaml"
    xaml.write_text(DRACULA_MINIMAL)

    written = convert_file(xaml, ThemeData(), tmp_path / "out")

    assert [p.name for p in written] == ["dracula.css"]
    assert "background-color: #282a36;" in written[0].read_text()


def test_convert_file_writes_light_and_dark_for_auto(tmp_path):
    xaml = tmp_path / "Circle System.xaml"
    xaml.write_text(AUTO_MINIMAL)

    written = convert_file(xaml, ThemeData(), tmp_path / "out")

    assert sorted(p.name for p in written) == ["circle-system-dark.css", "circle-system-light.css"]
