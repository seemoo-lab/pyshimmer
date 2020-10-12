from unittest import TestCase

import numpy as np

from pyshimmer.reader.shimmer_reader import unwrap_device_timestamps, fit_linear_1d


# noinspection PyMethodMayBeStatic
class UtilTest(TestCase):

    def test_unwrap_device_timestamps(self):
        ts_wrapped = np.array([0, 1, 2, 2 ** 24 - 1, 0, 2 ** 24])
        expected = np.array([0, 1, 2, 2 ** 24 - 1, 2 ** 24, 2 * 2 ** 24])
        actual = unwrap_device_timestamps(ts_wrapped)
        np.testing.assert_equal(actual, expected)

        ts_wrapped = np.array([0, 10, 20, 30, 5, 15, 25, 35])
        expected = np.array([0, 10, 20, 30, 5 + 2 ** 24, 15 + 2 ** 24, 25 + 2 ** 24, 35 + 2 ** 24])
        actual = unwrap_device_timestamps(ts_wrapped)
        np.testing.assert_equal(actual, expected)

    def test_fit_linear_1d(self):
        x = np.array([0, 1])
        y = np.array([0, 10])
        xi = np.array([0, 0.25, 0.5, 0.75, 1])

        yi_expected = np.array([0, 2.5, 5, 7.5, 10])
        yi_actual = fit_linear_1d(x, y, xi)
        np.testing.assert_almost_equal(yi_actual, yi_expected)

        xi = 0.1
        yi_expected = 1.0
        yi_actual = fit_linear_1d(x, y, xi)
        np.testing.assert_almost_equal(yi_actual, yi_expected)
