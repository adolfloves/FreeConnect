"""Логика восстановления и видимости стратегий (app-хелперы).

Покрывает три фикса «A»:
  - recovery переключается ТОЛЬКО на стратегию с живым Discord (не на YouTube-only);
  - автоподбор не прячет Discord-рабочую стратегию (кейс ALT9) из-за минуса голоса;
  - _score_to_item выставляет discord_ok/discord_sites_ok/youtube_ok корректно.
"""
import unittest

from freeconnect.app import (_extract_exe_from_zip, _is_offerable,
                             _pick_recovery_candidate, _score_to_item)
from freeconnect.autosearch import StrategyScore
from freeconnect.strategies import Strategy
from freeconnect.tester import ServiceResult, SiteResult


def _svc(service, ok_sites, voice=None):
    sites = [SiteResult(host=f"{service}{i}", ok=ok_sites) for i in range(3)]
    return ServiceResult(service=service, sites=sites, voice_ok=voice)


def _item(name, services):
    st = Strategy(id=name, name=name, source_bat="x", args=[])
    sc = StrategyScore(strategy=st, services=services)
    # проставляем working так же, как это делает autosearch._compute_score
    sc.working = sc.services_ok > 0
    return _score_to_item(sc)


class TestScoreToItemFlags(unittest.TestCase):
    def test_discord_dead_voice_sites_ok(self):
        # Discord открыт по сайтам, но голос мёртв, YouTube не открыт (кейс ALT9 у нас).
        it = _item("ALT9", [_svc("discord", True, voice=False), _svc("youtube", False)])
        self.assertFalse(it["discord_ok"])          # голос мёртв -> сервис не ок
        self.assertTrue(it["discord_sites_ok"])      # но сайты Discord открыты
        self.assertFalse(it["youtube_ok"])
        self.assertFalse(it["working"])              # строго — не рабочая

    def test_all_live(self):
        it = _item("ALT", [_svc("discord", True, voice=True), _svc("youtube", True)])
        self.assertTrue(it["discord_ok"])
        self.assertTrue(it["youtube_ok"])
        self.assertTrue(it["working"])


class TestOfferable(unittest.TestCase):
    def test_alt9_is_offerable_even_without_voice(self):
        it = _item("ALT9", [_svc("discord", True, voice=False), _svc("youtube", False)])
        self.assertTrue(_is_offerable(it))   # НЕ прячем — юзер сможет выбрать руками

    def test_dead_strategy_not_offerable(self):
        it = _item("DEAD", [_svc("discord", False, voice=False), _svc("youtube", False)])
        self.assertFalse(_is_offerable(it))


class TestRecoveryCandidate(unittest.TestCase):
    def test_skips_youtube_only(self):
        working = [
            {"name": "CUR", "discord_ok": True},
            {"name": "YT_ONLY", "discord_ok": False},   # только ютуб — пропустить
            {"name": "DISC2", "discord_ok": True},
        ]
        # текущая CUR -> следующий с живым Discord это DISC2, а не YT_ONLY
        self.assertEqual(_pick_recovery_candidate(working, "CUR"), "DISC2")

    def test_none_when_only_youtube_alternatives(self):
        working = [
            {"name": "CUR", "discord_ok": True},
            {"name": "YT_ONLY", "discord_ok": False},
        ]
        # единственная альтернатива — YouTube-only -> НЕ переключаемся (None)
        self.assertIsNone(_pick_recovery_candidate(working, "CUR"))

    def test_ignores_current_and_missing_flag(self):
        working = [
            {"name": "CUR", "discord_ok": True},
            {"name": "OLD_NO_FLAG"},                    # старый конфиг без discord_ok
            {"name": "GOOD", "discord_ok": True},
        ]
        self.assertEqual(_pick_recovery_candidate(working, "CUR"), "GOOD")


class TestExtractExeFromZip(unittest.TestCase):
    """Установщик из codeload-архива зеркала (файлы завёрнуты в подпапку)."""

    def _zip(self):
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("millerloves-freeconnect-mirror-dist-abc/README.md", "x")
            z.writestr("millerloves-freeconnect-mirror-dist-abc/FreeConnect-Setup.exe",
                       b"MZ-fake-installer")
        return buf.getvalue()

    def test_extracts_by_name(self):
        import os
        import tempfile
        dest = os.path.join(tempfile.mkdtemp(), "out.exe")
        _extract_exe_from_zip(self._zip(), "FreeConnect-Setup.exe", dest)
        with open(dest, "rb") as f:
            self.assertEqual(f.read(), b"MZ-fake-installer")

    def test_missing_exe_raises(self):
        import os
        import tempfile
        dest = os.path.join(tempfile.mkdtemp(), "out.exe")
        with self.assertRaises(RuntimeError):
            _extract_exe_from_zip(self._zip(), "NoSuch.exe", dest)


if __name__ == "__main__":
    unittest.main()
