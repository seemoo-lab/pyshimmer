# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2020  Lukas Magel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock

import numpy as np

from pyshimmer.util import PeekQueue
from pyshimmer.util import (
    bit_is_set,
    raise_to_next_pow,
    flatten_list,
    fmt_hex,
    unpack,
    unwrap,
    find_invalid_timestamps,
    reorder_window_ticks,
    TIMESTAMP_MODULO_3_BYTE,
    TIMESTAMP_WRAP_WINDOW,
    calibrate_u12_adc_value,
    battery_voltage_to_percent,
    FileIOBase,
)


class UtilTest(TestCase):

    def test_bit_is_set(self):
        r = bit_is_set(0x10, 0x01)
        self.assertEqual(r, False)

        r = bit_is_set(0x10, 0x10)
        self.assertEqual(r, True)

        r = bit_is_set(0x05, 0x01)
        self.assertEqual(r, True)

        r = bit_is_set(0x05, 0x02)
        self.assertEqual(r, False)

        r = bit_is_set(0x05, 0x04)
        self.assertEqual(r, True)

    def test_raise_to_next_pow(self):
        r = raise_to_next_pow(0)
        self.assertEqual(r, 1)

        r = raise_to_next_pow(1)
        self.assertEqual(r, 1)

        r = raise_to_next_pow(2)
        self.assertEqual(r, 2)

        r = raise_to_next_pow(3)
        self.assertEqual(r, 4)

        r = raise_to_next_pow(4)
        self.assertEqual(r, 4)

        r = raise_to_next_pow(6)
        self.assertEqual(r, 8)

        r = raise_to_next_pow(14)
        self.assertEqual(r, 16)

    def test_flatten_list(self):
        r = flatten_list([[10], [20]])
        self.assertEqual(r, [10, 20])

        r = flatten_list(((10,), (20,)))
        self.assertEqual(r, [10, 20])

        r = flatten_list([[10]])
        self.assertEqual(r, [10])

    def test_fmt_hex(self):
        r = fmt_hex(b"\x01")
        self.assertEqual(r, "01")

        r = fmt_hex(b"\x01\x02")
        self.assertEqual(r, "01 02")

    def test_unpack(self):
        r = unpack([10])

        self.assertEqual(r, 10)

        r = unpack([10, 20])
        self.assertEqual(r, [10, 20])

        r = unpack([])
        self.assertEqual(r, [])

        r = unpack(())
        self.assertEqual(r, ())

        r = unpack((10,))
        self.assertEqual(r, 10)

        r = unpack((10, 20))
        self.assertEqual(r, (10, 20))

    # noinspection PyMethodMayBeStatic
    def test_unwrap(self):
        shift = 10
        x = np.array([0, 1, 5, 8, 0, 2, 5, 10, 3, 7, 9])
        e = np.array([0, 1, 5, 8, 10, 12, 15, 20, 23, 27, 29])

        r = unwrap(x, shift)
        np.testing.assert_equal(r, e)

        x = np.array([0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2])
        e = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])

        r = unwrap(x, 4)
        np.testing.assert_equal(r, e)

        e = np.arange(0, 2000, 45)
        x = e % 250

        r = unwrap(x, 250)
        np.testing.assert_equal(r, e)

        e = np.arange(0, 4 * (2**24), 65)
        x = e % (2**24)

        r = unwrap(x, 2**24)
        np.testing.assert_equal(r, e)

    def test_find_invalid_timestamps(self):
        modulo = TIMESTAMP_MODULO_3_BYTE

        # A zero mid-range cannot be a counter origin: the firmware stamps a packet
        # when its sample tick starts it, so this record was never stamped.
        x = np.array([7406116, 7406506, 0, 7406571])
        e = np.array([False, False, True, False])
        np.testing.assert_equal(find_invalid_timestamps(x, modulo), e)

        # An overflow can legitimately land on zero. Its predecessor is then at the
        # very top of the range, which is what tells the two apart.
        x = np.array([modulo - 100, 0, 65])
        e = np.array([False, False, False])
        np.testing.assert_equal(find_invalid_timestamps(x, modulo), e)

        # Exactly on the boundary of the window, and just inside it.
        x = np.array([modulo - TIMESTAMP_WRAP_WINDOW, 0])
        np.testing.assert_equal(find_invalid_timestamps(x, modulo), [False, False])
        x = np.array([modulo - TIMESTAMP_WRAP_WINDOW - 1, 0])
        np.testing.assert_equal(find_invalid_timestamps(x, modulo), [False, True])

        # The first sample has nothing before it to contradict a zero.
        x = np.array([0, 65, 130])
        np.testing.assert_equal(find_invalid_timestamps(x, modulo), [False] * 3)

        # Narrower counters are never flagged: their whole range is 2 seconds, so a
        # stall really can cross one.
        x = np.array([30000, 0, 65])
        np.testing.assert_equal(find_invalid_timestamps(x, 2**16), [False] * 3)

        # Only an exact zero is exempt.
        x = np.array([7406506, 1])
        np.testing.assert_equal(find_invalid_timestamps(x, modulo), [False, False])

    def test_unwrap_ignores_invalid_timestamps(self):
        modulo = TIMESTAMP_MODULO_3_BYTE

        # The sequence recovered from an affected recording. Read naively, the zero
        # is an overflow and every later sample gains 512 seconds.
        x = np.array([7406116, 7406506, 0, 7406571])
        invalid = find_invalid_timestamps(x, modulo)

        r = unwrap(x.copy(), modulo, invalid=invalid)
        self.assertEqual(r[-1] - r[0], 455, "four records span 455 ticks, not a modulo")

        # Without the mask, the old behaviour - kept so the difference is explicit.
        r_naive = unwrap(x.copy(), modulo)
        self.assertEqual(r_naive[-1] - r_naive[0], 455 + modulo)

        # A genuine overflow is still unwrapped when a mask is supplied.
        x = np.array([modulo - 65, 0, 65])
        invalid = find_invalid_timestamps(x, modulo)
        r = unwrap(x.copy(), modulo, invalid=invalid)
        np.testing.assert_equal(r, [modulo - 65, modulo, modulo + 65])

        # A recording with several bad records gains nothing at all.
        period = 65
        n = 800
        x = np.arange(n, dtype=np.int64) * period + 1000000
        for bad in (200, 400, 600):
            x[bad] = 0
        invalid = find_invalid_timestamps(x, modulo)
        self.assertEqual(invalid.sum(), 3)

        r = unwrap(x.copy(), modulo, invalid=invalid)
        clean = r[~invalid]
        self.assertTrue(np.all(np.diff(clean) > 0), "timeline stays monotonic")
        self.assertEqual(clean[-1] - clean[0], (n - 1) * period)

    def test_reorder_window_ticks(self):
        modulo = TIMESTAMP_MODULO_3_BYTE

        # Eight sample periods. The header divider is the period in ticks directly.
        self.assertEqual(reorder_window_ticks(65, modulo), 520)
        self.assertEqual(reorder_window_ticks(640, 2**16), 5120)

        # Clamped, so a very low rate cannot produce a window at or above the modulo,
        # which would leave no backward step large enough to be an overflow.
        self.assertEqual(reorder_window_ticks(32768, 2**16), 2**16 / 8)

        # An unknown period disables the branch. It must never become an infinite
        # window: that would read every backward step as a reorder and lose every
        # overflow, which is worse than no reorder detection at all.
        self.assertEqual(reorder_window_ticks(None, modulo), 0.0)
        self.assertEqual(reorder_window_ticks(0, modulo), 0.0)
        self.assertEqual(reorder_window_ticks(-5, modulo), 0.0)

    def test_unwrap_places_reordered_packets(self):
        modulo = TIMESTAMP_MODULO_3_BYTE
        w = reorder_window_ticks(65, modulo)

        # Two adjacent packets the wrong way round. Each is placed where it was taken,
        # so the result is deliberately not monotonic - and no modulo is added.
        x = np.array([1000, 1130, 1065, 1195])
        r = unwrap(x.copy(), modulo, reorder_window=w)
        np.testing.assert_equal(r, [1000, 1130, 1065, 1195])

        # Without the window the same input reads as an overflow, which is what every
        # Shimmer host API used to do.
        r_naive = unwrap(x.copy(), modulo)
        self.assertEqual(r_naive[2], 1065 + modulo)

    def test_unwrap_handles_a_packet_late_from_before_an_overflow(self):
        modulo = TIMESTAMP_MODULO_3_BYTE
        w = reorder_window_ticks(65, modulo)

        # The third sample arrives late from before the boundary. Comparing unwrapped
        # values rather than modular distances misses it: its value looks like forward
        # motion of nearly a whole modulo, so it is accepted, and the fourth sample is
        # then read as a second overflow. Two modulos from one out-of-order packet.
        x = np.array([modulo - 10, 5, modulo - 10, 70])
        r = unwrap(x, modulo, reorder_window=w)
        np.testing.assert_equal(r, [modulo - 10, modulo + 5, modulo - 10, modulo + 70])

    def test_unwrap_keeps_an_overflow_after_heavy_loss(self):
        modulo = TIMESTAMP_MODULO_3_BYTE
        w = reorder_window_ticks(65, modulo)

        # Forward motion is the default, so an overflow preceded by a long dropout is
        # still an overflow however much was lost before it.
        r = unwrap(np.array([16000000, 100]), modulo, reorder_window=w)
        np.testing.assert_equal(r, [16000000, modulo + 100])

    def test_unwrap_does_not_misread_a_dropout_across_a_16bit_overflow(self):
        # 1.8 s lost across the 2 s counter - an ordinary Bluetooth gap. A window sized
        # as a fraction of the modulo reads this as a reordered packet and silently
        # loses the overflow; eight sample periods does not.
        modulo = 2**16
        w = reorder_window_ticks(640, modulo)  # 51.2 Hz
        lost = int(1.8 * 32768)
        before = 60000

        r = unwrap(
            np.array([before, (before + lost) % modulo]), modulo, reorder_window=w
        )
        np.testing.assert_equal(r, [before, before + lost])

    def test_unwrap_does_not_modify_its_input(self):
        x = np.array([modulo := TIMESTAMP_MODULO_3_BYTE - 10, 5])
        before = x.copy()
        unwrap(x, TIMESTAMP_MODULO_3_BYTE)
        np.testing.assert_equal(x, before)

    def test_find_invalid_timestamps_holds_its_predecessor_across_a_run(self):
        modulo = TIMESTAMP_MODULO_3_BYTE

        # Consecutive invalid records are each judged against the last record that
        # carried a timestamp, not against the zero before them.
        x = np.array([7406506, 0, 0, 7406571])
        np.testing.assert_equal(
            find_invalid_timestamps(x, modulo), [False, True, True, False]
        )

        # A zero close enough to the origin to be a reordered packet is not invalid -
        # reorder is tested first, and unwrap places it.
        x = np.array([300, 365, 0, 430])
        w = reorder_window_ticks(65, modulo)
        np.testing.assert_equal(
            find_invalid_timestamps(x, modulo, reorder_window=w), [False] * 4
        )

    def test_shared_conformance_vectors(self):
        """Run the vectors every Shimmer host API is checked against.

        They live in the firmware repository beside the rule they encode, and every
        other Shimmer host API runs the same file. Five implementations of one wire
        format drifted apart once already - the same unwrap defect sat in all five -
        and reviewing them against each other by hand is what let that happen. If this
        test and its counterparts disagree, one of them is wrong.
        """
        path = Path(__file__).parent / "resources" / "timestamp_unwrap.json"
        doc = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(doc["revision"], 1, "vector file revision")
        self.assertEqual(doc["ticksPerSecond"], 32768)
        self.assertEqual(doc["invalidZeroWindowTicks"], TIMESTAMP_WRAP_WINDOW)

        # A vector that stops being run is a vector that stops protecting anything,
        # and a loop over whatever the file happens to hold would not notice it go.
        # Updating this list is the moment to ask what changed upstream.
        self.assertEqual(
            [v["id"] for v in doc["vectors"]],
            [
                "monotonic-24bit",
                "wrap-24bit",
                "wrap-lands-on-zero-24bit",
                "invalid-zero-signature-24bit",
                "invalid-zero-no-cascade-24bit",
                "first-sample-zero-24bit",
                "wrap-16bit",
                "zero-on-16bit-is-a-wrap",
                "backward-step-outside-window-is-a-wrap-24bit",
                "duplicate-24bit",
                "reorder-one-period-24bit",
                "reorder-one-period-16bit",
                "reorder-across-wrap-boundary-24bit",
                "wrap-after-heavy-loss-24bit",
                "wrap-after-heavy-loss-16bit",
                "wrap-spanning-dropout-1p8s-16bit",
                "wrap-spanning-dropout-152s-24bit",
                "rate-unknown-backward-step-is-a-wrap-24bit",
                "rate-unknown-zero-still-rejected-24bit",
                "zero-within-window-of-origin-24bit",
                "zero-within-window-after-wrap-24bit",
                "reorder-window-boundary-inclusive-24bit",
                "reorder-window-boundary-exclusive-24bit",
                "low-rate-clamp-16bit",
                "high-rate-reorder-24bit",
                "reorder-beyond-eight-periods-is-a-wrap-24bit",
                "reorder-onto-origin-then-earlier-packet-24bit",
            ],
        )

        for vector in doc["vectors"]:
            vid = vector["id"]
            modulo = vector["modulo"]
            window = vector["reorderWindowTicks"]
            x = np.array(vector["raw"], dtype=np.int64)

            invalid = find_invalid_timestamps(x, modulo, reorder_window=window)
            np.testing.assert_equal(
                invalid, vector["expectedRejected"], err_msg=f"{vid}: rejected"
            )

            r = unwrap(x, modulo, invalid=invalid, reorder_window=window)
            np.testing.assert_equal(
                r, vector["expectedUnwrapped"], err_msg=f"{vid}: unwrapped"
            )
            self.assertEqual(
                int(r[-1] // modulo),
                vector["expectedFinalCycle"],
                f"{vid}: final cycle",
            )

        for case in doc["windowDerivation"]["cases"]:
            rate = case["samplingRateHz"]
            modulo = 2 ** case["timestampBits"]
            period = None if not rate or rate <= 0 else 32768 / rate
            self.assertAlmostEqual(
                reorder_window_ticks(period, modulo),
                case["expectedReorderWindowTicks"],
                delta=max(case["tolerance"], 1e-9),
                msg=f"window for rate {rate} at modulo {modulo}",
            )

    def test_calibrate_u12_adc_value(self):
        uncalibratedData = 2863
        offset = 0
        vRefP = 3.0
        gain = 1.0

        actual = calibrate_u12_adc_value(uncalibratedData, offset, vRefP, gain)

        desired = 2.0974358974358975
        np.testing.assert_almost_equal(actual, desired)

    def test_battery_voltage_to_percent(self):
        voltage = 3.9078
        desired = 72.8

        actual = battery_voltage_to_percent(voltage)
        np.testing.assert_equal(actual, desired)

    def test_peek_queue(self):
        queue = PeekQueue()

        queue.put(1)
        queue.put(2)
        queue.put(3)

        self.assertEqual(queue.peek(), 1)
        queue.get()

        self.assertEqual(queue.peek(), 2)
        queue.get()

        self.assertEqual(queue.peek(), 3)
        queue.get()

        self.assertEqual(queue.peek(), None)

    def test_file_io_base(self):
        input_bin = bytes(range(255))
        io_obj = BytesIO(input_bin)

        sut = FileIOBase(io_obj)
        self.assertEqual(sut._tell(), 0)

        sut._seek(10)
        self.assertEqual(sut._tell(), 10)

        sut._seek_relative(-2)
        self.assertEqual(sut._tell(), 8)

        r = sut._read(2)
        self.assertEqual(r, b"\x08\x09")

        r = sut._read_packed("<H")
        self.assertEqual(r, 0x0B0A)

    def test_file_io_base_not_seekable(self):
        mock = Mock(spec=BytesIO)
        mock.seekable.return_value = False

        self.assertRaises(ValueError, FileIOBase, mock)
