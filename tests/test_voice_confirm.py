"""Гайд-подтверждение голоса (ground truth от живого Discord) — машина состояний.

Проверяем backend-поток `_run_deep_guided`: сбор шорт-листа, ожидание вердикта
человека по кандидату, фиксация первого подтверждённого, честный «не подтверждён».
"""
import threading
import time
import unittest

from freeconnect import app as fcapp
from freeconnect import custom, deepsearch
from freeconnect.autosearch import StrategyScore
from freeconnect.strategies import Strategy
from freeconnect.tester import ServiceResult, SiteResult


def _sc(name):
    st = Strategy(id=name, name=name, source_bat="x", args=["--a"])
    disc = ServiceResult(service="discord",
                         sites=[SiteResult(host=f"d{i}", ok=True) for i in range(3)])
    yt = ServiceResult(service="youtube",
                       sites=[SiteResult(host=f"y{i}", ok=True) for i in range(3)])
    return StrategyScore(strategy=st, services=[disc, yt])


def _fake_api():
    api = fcapp.Api.__new__(fcapp.Api)          # без тяжёлого __init__
    api._cancel = threading.Event()
    api._vc_event = threading.Event()
    api._vc_verdict = None
    api._searching = True
    api.strategy_name = None
    api.working = []
    api.enabled = False

    class _Eng:
        started = []
        stopped = 0
        def start(self, cand, *a, **k):
            _Eng.started.append(getattr(cand, "name", cand))
        def stop(self, *a, **k):
            _Eng.stopped += 1
    api.engine = _Eng()
    api._save = lambda: None
    api._start_monitors = lambda: None
    api._start_doh_async = lambda: None
    api._state = lambda: {"working": api.working}
    api._pushes = []
    api._push = lambda ev, *a: api._pushes.append((ev, a))
    return api


def _wait_probe(api, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        if any(ev == "onVoiceConfirmProbe" for ev, _ in api._pushes):
            return True
        time.sleep(0.01)
    return False


class TestGuidedVoiceConfirm(unittest.TestCase):
    def setUp(self):
        self._collect = deepsearch.collect_site_candidates
        self._add = custom.add_custom

    def tearDown(self):
        deepsearch.collect_site_candidates = self._collect
        custom.add_custom = self._add

    def test_confirm_locks_current_candidate(self):
        deepsearch.collect_site_candidates = lambda *a, **k: [_sc("c1"), _sc("c2")]
        custom.add_custom = lambda args, base_name=None, label=None: Strategy(
            id="FreeConnect #1", name="FreeConnect #1 голос подтверждён",
            source_bat="x", args=args)
        api = _fake_api()
        base = Strategy(id="ALT", name="ALT", source_bat="x", args=[])
        t = threading.Thread(target=api._run_deep_guided, args=(base,))
        t.start()
        self.assertTrue(_wait_probe(api))
        api.voice_confirm_result(True)             # человек: «голос подключился»
        t.join(timeout=3)
        self.assertFalse(t.is_alive())
        self.assertIn("подтверждён", api.strategy_name)
        self.assertTrue(api.enabled)
        done = [a[0] for ev, a in api._pushes if ev == "onVoiceConfirmDone"]
        self.assertTrue(done and done[0]["confirmed"])

    def test_next_then_confirm_second(self):
        deepsearch.collect_site_candidates = lambda *a, **k: [_sc("c1"), _sc("c2")]
        custom.add_custom = lambda args, base_name=None, label=None: Strategy(
            id="ok", name="FreeConnect #2 голос подтверждён", source_bat="x", args=args)
        api = _fake_api()
        base = Strategy(id="ALT", name="ALT", source_bat="x", args=[])
        t = threading.Thread(target=api._run_deep_guided, args=(base,))
        t.start()
        self.assertTrue(_wait_probe(api))
        api.voice_confirm_result(False)            # первый — «дальше»
        time.sleep(0.05)
        api.voice_confirm_result(True)             # второй — подтвердил
        t.join(timeout=3)
        probes = [a[0] for ev, a in api._pushes if ev == "onVoiceConfirmProbe"]
        self.assertEqual(len(probes), 2)           # дошли до второго кандидата
        self.assertEqual(api.engine.started, ["c1", "c2"])

    def test_no_confirm_reports_unconfirmed(self):
        deepsearch.collect_site_candidates = lambda *a, **k: [_sc("only")]
        api = _fake_api()
        base = Strategy(id="ALT", name="ALT", source_bat="x", args=[])
        t = threading.Thread(target=api._run_deep_guided, args=(base,))
        t.start()
        self.assertTrue(_wait_probe(api))
        api.voice_confirm_result(False)            # «дальше» на единственном
        t.join(timeout=3)
        done = [a[0] for ev, a in api._pushes if ev == "onVoiceConfirmDone"]
        self.assertTrue(done and not done[0]["confirmed"])
        self.assertGreaterEqual(api.engine.stopped, 1)   # движок погашен

    def test_empty_shortlist(self):
        deepsearch.collect_site_candidates = lambda *a, **k: []
        api = _fake_api()
        base = Strategy(id="ALT", name="ALT", source_bat="x", args=[])
        api._run_deep_guided(base)
        done = [a[0] for ev, a in api._pushes if ev == "onVoiceConfirmDone"]
        self.assertTrue(done and done[0].get("empty"))

    def test_cancel_during_wait(self):
        deepsearch.collect_site_candidates = lambda *a, **k: [_sc("c1")]
        api = _fake_api()
        base = Strategy(id="ALT", name="ALT", source_bat="x", args=[])
        t = threading.Thread(target=api._run_deep_guided, args=(base,))
        t.start()
        self.assertTrue(_wait_probe(api))
        api._cancel.set()
        api._vc_event.set()                        # как cancel_search
        t.join(timeout=3)
        self.assertFalse(t.is_alive())


if __name__ == "__main__":
    unittest.main()
