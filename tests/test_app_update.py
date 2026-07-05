"""Сравнение версий для автообновления приложения (app_update)."""
import unittest

from freeconnect import app_update as au


class TestParseVer(unittest.TestCase):
    def test_v_prefix_and_plain(self):
        self.assertEqual(au._parse_ver("v1.2.3"), (1, 2, 3))
        self.assertEqual(au._parse_ver("1.2"), (1, 2))

    def test_empty_and_garbage(self):
        self.assertEqual(au._parse_ver(""), (0,))
        self.assertEqual(au._parse_ver("beta"), (0,))


class TestIsNewer(unittest.TestCase):
    def test_newer(self):
        self.assertTrue(au._is_newer("v0.1.1", "0.1.0"))
        self.assertTrue(au._is_newer("v1.0", "0.9"))
        self.assertTrue(au._is_newer("1.0.1", "1.0"))  # разная длина

    def test_equal_or_older(self):
        self.assertFalse(au._is_newer("0.1.0", "0.1.0"))
        self.assertFalse(au._is_newer("1.0", "1.0.0"))  # равны после выравнивания
        self.assertFalse(au._is_newer("0.1.0", "v0.1.1"))


class TestCheckGuards(unittest.TestCase):
    def test_repo_configured(self):
        # На случай, если кто-то забудет заполнить константу перед сборкой.
        self.assertNotIn("__", au.GITHUB_REPO)
        self.assertIn("/", au.GITHUB_REPO)


if __name__ == "__main__":
    unittest.main()
