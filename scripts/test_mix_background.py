import unittest
import numpy as np
from mix_background import mix, RATE


class MixTests(unittest.TestCase):
    def test_voice_preserved_and_pauses_smooth(self):
        t = np.arange(RATE * 6) / RATE
        voice = np.repeat((.12 * np.sin(2 * np.pi * 400 * t))[:, None], 2, axis=1)
        voice[3 * RATE:] = 0
        music = np.full_like(voice, .1)
        mixed, bed, report = mix(voice, music)
        np.testing.assert_allclose(mixed - bed, voice, atol=1e-8)
        self.assertLess(abs(report['measured_active_voice_music_gap_db'] - 24), 2)
        self.assertLess(np.max(np.abs(np.diff(bed[:, 0]))), .0001)
        self.assertLess(report['peak'], .98)
        self.assertGreater(bed[4 * RATE, 0], bed[2 * RATE, 0])

    def test_short_music_and_silent_voice_rejected(self):
        with self.assertRaises(ValueError):
            mix(np.ones((1000, 2)) * .1, np.ones((500, 2)))
        with self.assertRaises(ValueError):
            mix(np.zeros((1000, 2)), np.ones((1000, 2)))


if __name__ == '__main__':
    unittest.main()
