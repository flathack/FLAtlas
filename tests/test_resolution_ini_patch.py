from fl_editor.resolution_ini_patch import patch_freelancer_display_text, patch_perfoptions_resolution_text


def test_patch_perfoptions_resolution_text_updates_existing_display_section():
    raw = "[Display]\nsize= 800, 600\n"

    text, changed = patch_perfoptions_resolution_text(raw, 1920, 1080, set_color_depth_32=True)

    assert changed is True
    assert "size= 1920, 1080" in text
    assert "color depth= 32" in text


def test_patch_perfoptions_resolution_text_creates_display_section_when_missing():
    text, changed = patch_perfoptions_resolution_text("", 1280, 720)

    assert changed is True
    assert text == "[Display]\nsize= 1280, 720\n"


def test_patch_freelancer_display_text_updates_existing_display_sections():
    raw = "[;Display]\nsize = 800,600\n\n[Display]\nsize = 1024,768\n"

    text, changed = patch_freelancer_display_text(raw, 1920, 1080, set_color_depth_32=True)

    assert changed is True
    assert text.count("size = 1920,1080") == 2
    assert "color_bpp = 32" in text
    assert "depth_bpp = 32" in text


def test_patch_freelancer_display_text_creates_display_when_missing():
    text, changed = patch_freelancer_display_text("[Freelancer]\nfoo = bar\n", 1600, 900)

    assert changed is True
    assert "[Display]" in text
    assert "size = 1600,900" in text
