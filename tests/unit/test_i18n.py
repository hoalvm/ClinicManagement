"""Unit tests for the i18n translation system and language switching."""

from frontend.core.i18n import I18nManager, get_i18n, t
from frontend.core.translations import TRANSLATIONS, get_translation


def test_translations_dictionary_symmetry():
    """Ensure all translation keys have non-empty Vietnamese and English entries."""
    for key, val in TRANSLATIONS.items():
        assert "vi" in val, f"Key '{key}' missing 'vi' translation"
        assert "en" in val, f"Key '{key}' missing 'en' translation"
        assert len(val["vi"].strip()) > 0, f"Key '{key}' has empty 'vi' translation"
        assert len(val["en"].strip()) > 0, f"Key '{key}' has empty 'en' translation"


def test_get_translation_basic():
    vi_text = get_translation("sign_in_button", lang="vi")
    en_text = get_translation("sign_in_button", lang="en")
    assert vi_text == "Đăng nhập"
    assert en_text == "Sign in"


def test_get_translation_interpolation():
    vi_text = get_translation("affiliated_doctors", lang="vi", count=3)
    en_text = get_translation("affiliated_doctors", lang="en", count=3)
    assert "3" in vi_text
    assert "3" in en_text


def test_get_translation_fallback():
    res = get_translation("non_existent_key", lang="vi", default="Fallback text")
    assert res == "Fallback text"

    res_no_default = get_translation("non_existent_key_no_def", lang="vi")
    assert res_no_default == "non_existent_key_no_def"


def test_i18n_manager_switching():
    i18n = I18nManager()
    events: list[str] = []
    i18n.language_changed.connect(events.append)

    # Force switch to opposite first to guarantee a change event
    first_target = "vi" if i18n.current_language == "en" else "en"
    second_target = "en" if first_target == "vi" else "vi"

    i18n.set_language(first_target)
    assert i18n.current_language == first_target

    i18n.set_language(second_target)
    assert i18n.current_language == second_target

    assert first_target in events
    assert second_target in events


def test_global_t_helper():
    i18n = get_i18n()
    i18n.set_language("vi")
    assert t("username") == "Tên đăng nhập"
    i18n.set_language("en")
    assert t("username") == "Username"
