import mmap
import unittest

from ovb_rc003.runtime_status import RuntimeStatusChannel, STATUS_SIZE


class RuntimeStatusChannelTests(unittest.TestCase):
    def setUp(self):
        self.now_ns = 1_000_000_000_000
        self.shared = mmap.mmap(-1, STATUS_SIZE)

    def tearDown(self):
        self.shared.close()

    def channel(self):
        return RuntimeStatusChannel(
            buffer=self.shared,
            clock_ns=lambda: self.now_ns,
        )

    def test_uninitialized_mapping_is_inactive(self):
        self.assertEqual(self.channel().read().level, 0.0)
        self.assertFalse(self.channel().read().active)
        self.assertFalse(self.channel().read().fresh)

    def test_publish_round_trips_between_two_channel_instances(self):
        writer = self.channel()
        reader = self.channel()
        writer.publish(0.625, True)
        status = reader.read()
        self.assertAlmostEqual(status.level, 0.625, places=5)
        self.assertTrue(status.active)
        self.assertTrue(status.fresh)

    def test_publish_clamps_level(self):
        writer = self.channel()
        writer.publish(4.0, True)
        self.assertEqual(self.channel().read().level, 1.0)
        writer.publish(-3.0, True)
        self.assertEqual(self.channel().read().level, 0.0)

    def test_stale_status_fails_closed_to_inactive_zero(self):
        writer = self.channel()
        writer.publish(0.8, True)
        self.now_ns += 2_000_000_000
        status = self.channel().read(max_age_seconds=1.0)
        self.assertEqual(status.level, 0.0)
        self.assertFalse(status.active)
        self.assertFalse(status.fresh)

    def test_reset_publishes_a_fresh_inactive_state(self):
        writer = self.channel()
        writer.publish(0.8, True)
        writer.reset()
        status = self.channel().read()
        self.assertEqual(status.level, 0.0)
        self.assertFalse(status.active)
        self.assertTrue(status.fresh)


if __name__ == "__main__":
    unittest.main()
