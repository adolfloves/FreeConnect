"""STUN-пакет (мелкий и большой) и гейтинг голоса в ServiceResult (tester)."""
import struct
import unittest

from freeconnect.tester import ServiceResult, SiteResult, _stun_packet


def _svc(service, n_ok, n_total, voice=None):
    sites = [SiteResult(host=f"h{i}", ok=(i < n_ok)) for i in range(n_total)]
    return ServiceResult(service=service, sites=sites, voice_ok=voice)


class TestStunPacket(unittest.TestCase):
    def test_small_packet_header(self):
        txid, pkt = _stun_packet(0)
        self.assertEqual(len(pkt), 20)
        mtype, mlen, cookie = struct.unpack("!HHI", pkt[:8])
        self.assertEqual(mtype, 0x0001)          # Binding Request
        self.assertEqual(mlen, 0)                # без атрибутов
        self.assertEqual(cookie, 0x2112A442)     # magic cookie
        self.assertEqual(pkt[8:20], txid)

    def test_big_packet_padding(self):
        _, pkt = _stun_packet(1000)
        # header(20) + attr-header(4) + value(1000) = 1024, длина кратна 4
        self.assertEqual(len(pkt), 1024)
        self.assertEqual((len(pkt) - 20) % 4, 0)
        _, mlen, _ = struct.unpack("!HHI", pkt[:8])
        self.assertEqual(mlen, len(pkt) - 20)    # поле длины = размер атрибутов


class TestVoiceGating(unittest.TestCase):
    def test_sites_ok_needs_majority(self):
        self.assertTrue(_svc("youtube", 2, 3).sites_ok)   # 2/3 >= ceil(3/2)=2
        self.assertFalse(_svc("youtube", 1, 3).sites_ok)  # 1/3 < 2

    def test_youtube_no_voice_ok_equals_sites(self):
        s = _svc("youtube", 3, 3, voice=None)
        self.assertTrue(s.ok)

    def test_discord_dead_voice_fails_even_if_sites_ok(self):
        s = _svc("discord", 3, 3, voice=False)
        self.assertTrue(s.sites_ok)
        self.assertFalse(s.ok)   # ключевой инвариант: сайт открыт, но голос мёртв -> не ок

    def test_discord_live_voice_ok(self):
        self.assertTrue(_svc("discord", 3, 3, voice=True).ok)


if __name__ == "__main__":
    unittest.main()
