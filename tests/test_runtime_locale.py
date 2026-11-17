import tempfile
import unittest
from pathlib import Path

from noesis_harness import runtime_locale as rl


class RuntimeLocaleTests(unittest.TestCase):
    def test_default_lang_is_en(self):
        settings = rl.LocaleSettings()
        self.assertEqual(settings.get_lang(), "en")

    def test_set_ru_persists_on_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locale_settings.json"
            settings = rl.LocaleSettings(path=path)
            settings.set_lang("ru")
            settings.save()
            reloaded = rl.LocaleSettings.load(path)
            self.assertEqual(reloaded.get_lang(), "ru")

    def test_set_en_persists_on_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "locale_settings.json"
            rl.LocaleSettings("ru", path).save()
            settings = rl.LocaleSettings.load(path)
            settings.set_lang("en")
            settings.save()
            self.assertEqual(rl.LocaleSettings.load(path).get_lang(), "en")

    def test_invalid_lang_rejected(self):
        settings = rl.LocaleSettings()
        for bad in ("fr", "EN", "ruu", "", "de"):
            with self.assertRaises(ValueError):
                settings.set_lang(bad)

    def test_invalid_lang_constructor_rejected(self):
        with self.assertRaises(ValueError):
            rl.LocaleSettings("fr")

    def test_load_missing_file_defaults_to_en(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "does_not_exist.json"
            settings = rl.LocaleSettings.load(path)
            self.assertEqual(settings.get_lang(), "en")

    def test_load_corrupt_file_falls_back_to_en(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "corrupt.json"
            path.write_text("{not valid json", encoding="utf-8")
            settings = rl.LocaleSettings.load(path)
            self.assertEqual(settings.get_lang(), "en")

    def test_load_unknown_lang_falls_back_to_en(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "weird.json"
            path.write_text('{"lang": "zz"}', encoding="utf-8")
            self.assertEqual(rl.LocaleSettings.load(path).get_lang(), "en")

    def test_string_fallback_to_en_on_missing_lang(self):
        self.assertEqual(rl.get("status", "fr"), rl.STRINGS["en"]["status"])
        self.assertEqual(rl.get("status", "ru"), rl.STRINGS["ru"]["status"])

    def test_string_fallback_on_missing_key(self):
        value = rl.get("no_such_key", "en")
        self.assertEqual(value, "no_such_key")

    def test_responder_formatting_en(self):
        responder = rl.Responder(rl.LocaleSettings("en"))
        out = responder.respond("status", status="ok")
        self.assertEqual(out, "Status: ok")

    def test_responder_formatting_ru(self):
        responder = rl.Responder(rl.LocaleSettings("ru"))
        out = responder.respond("status", status="готово")
        self.assertEqual(out, rl.STRINGS["ru"]["status"].format(status="готово"))

    def test_responder_override_lang_arg(self):
        responder = rl.Responder(rl.LocaleSettings("en"))
        out = responder.respond("status", lang="ru", status="готово")
        self.assertEqual(out, "Статус: готово")

    def test_responder_missing_kwargs_returns_template(self):
        responder = rl.Responder(rl.LocaleSettings("en"))
        out = responder.respond("status")
        self.assertEqual(out, "Status: {status}")

    def test_save_load_round_trip_no_other_state_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rt.json"
            first = rl.LocaleSettings("ru", path)
            first.save()
            second = rl.LocaleSettings.load(path)
            self.assertEqual(first.get_lang(), second.get_lang())
            self.assertEqual(second.get_lang(), "ru")

    def test_responder_does_not_mutate_settings(self):
        settings = rl.LocaleSettings("en")
        responder = rl.Responder(settings)
        responder.respond("status", lang="ru", status="x")
        self.assertEqual(settings.get_lang(), "en")

    def test_unsupported_langs_constant(self):
        self.assertEqual(set(rl.SUPPORTED_LANGS), {"en", "ru"})


if __name__ == "__main__":
    unittest.main()
