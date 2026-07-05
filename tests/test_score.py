"""Метки/подсчёт рабочих сервисов у StrategyScore (autosearch).
Определяет имя своей стратегии (All / Discord / YouTube) и решение о сохранении."""
import unittest

from freeconnect.autosearch import StrategyScore
from freeconnect.strategies import Strategy
from freeconnect.tester import ServiceResult, SiteResult


def _svc(service, ok_sites, voice=None):
    sites = [SiteResult(host=f"h{i}", ok=True) for i in range(3)] if ok_sites else \
            [SiteResult(host=f"h{i}", ok=False) for i in range(3)]
    return ServiceResult(service=service, sites=sites, voice_ok=voice)


def _score(services):
    st = Strategy(id="x", name="x", source_bat="x", args=[])
    return StrategyScore(strategy=st, services=services)


class TestWorkingServices(unittest.TestCase):
    def test_only_passing_listed(self):
        sc = _score([_svc("discord", True, voice=True), _svc("youtube", False)])
        self.assertEqual(sc.working_services, ["discord"])
        self.assertEqual(sc.services_ok, 1)


class TestResultLabel(unittest.TestCase):
    def test_all_when_every_service_ok(self):
        sc = _score([_svc("discord", True, voice=True), _svc("youtube", True)])
        self.assertEqual(sc.result_label(), "All")

    def test_discord_only(self):
        sc = _score([_svc("discord", True, voice=True), _svc("youtube", False)])
        self.assertEqual(sc.result_label(), "Discord")

    def test_youtube_only_when_voice_dead(self):
        # Discord-сайт открыт, но голос мёртв -> Discord не считается -> только YouTube.
        sc = _score([_svc("discord", True, voice=False), _svc("youtube", True)])
        self.assertEqual(sc.result_label(), "YouTube")

    def test_empty_when_nothing_works(self):
        sc = _score([_svc("discord", False, voice=False), _svc("youtube", False)])
        self.assertEqual(sc.result_label(), "")


if __name__ == "__main__":
    unittest.main()
