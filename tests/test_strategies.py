"""Санитайзер аргументов и подстановка путей/игровых портов (strategies)."""
import unittest

from freeconnect.strategies import Strategy, _sanitize_args


class TestSanitize(unittest.TestCase):
    def test_drops_caret_and_percent(self):
        args = ["--ok=1", "--bad=^!", "--var=%UNRESOLVED%", "--good=2"]
        self.assertEqual(_sanitize_args(args), ["--ok=1", "--good=2"])

    def test_drops_zero_fake_tls(self):
        self.assertEqual(_sanitize_args(["--dpi-desync-fake-tls=0x00000000", "--x"]), ["--x"])

    def test_keeps_normal(self):
        args = ["--dpi-desync=fake,split2", "--dpi-desync-fooling=md5sig"]
        self.assertEqual(_sanitize_args(args), args)


class TestResolveArgs(unittest.TestCase):
    def _mk(self, args):
        return Strategy(id="x", name="x", source_bat="x", args=args)

    def test_game_filter_on_off(self):
        st = self._mk(["--wf-tcp={GAME_TCP}", "--wf-udp={GAME_UDP}"])
        on = st.resolve_args(game_filter=True)
        off = st.resolve_args(game_filter=False)
        self.assertEqual(on, ["--wf-tcp=1024-65535", "--wf-udp=1024-65535"])
        self.assertEqual(off, ["--wf-tcp=12", "--wf-udp=12"])

    def test_path_placeholders_substituted(self):
        st = self._mk(["--hostlist={LISTS}/l.txt", "--fake={BIN}/f.bin"])
        out = st.resolve_args(game_filter=False)
        # плейсхолдеры должны исчезнуть, пути стать абсолютными (с прямыми слэшами)
        self.assertFalse(any("{" in a for a in out))
        self.assertTrue(out[0].endswith("/l.txt"))
        self.assertTrue(out[1].endswith("/f.bin"))
        self.assertIn("runtime", out[0].replace("\\", "/").lower())


if __name__ == "__main__":
    unittest.main()
