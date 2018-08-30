from __future__ import absolute_import, division, print_function, unicode_literals
import numpy as np
from banzai.qc import pattern_noise
from banzai.tests.utils import FakeImage, gaussian2d
import pytest
import mock


@pytest.fixture(scope='module')
def set_random_seed():
    np.random.seed(200)


def test_no_input_images(set_random_seed):
    detector = pattern_noise.PatternNoiseDetector(None)
    images = detector.do_stage([])
    assert len(images) == 0


def test_group_by_keywords(set_random_seed):
    detector = pattern_noise.PatternNoiseDetector(None)
    assert detector.group_by_keywords is None


def test_pattern_noise_detects_noise_when_it_should(set_random_seed):
    data = 100.0 * np.sin(np.arange(1000000) / 0.1) + 1000.0 + np.random.normal(0.0, 10.0, size=1000000)
    data = data.reshape(1000, 1000)
    detector = pattern_noise.PatternNoiseDetector(None)
    assert detector.check_for_pattern_noise(data)


def test_pattern_noise_does_not_detect_white_noise(set_random_seed):
    data = 1000 + np.random.normal(0.0, 10.0, size=1000000)
    data = data.reshape(1000, 1000)
    detector = pattern_noise.PatternNoiseDetector(None)
    assert detector.check_for_pattern_noise(data) == False


def test_pattern_noise_on_garbage_image():
    data = np.zeros((1000, 1000))
    data[:, :] = np.nan
    detector = pattern_noise.PatternNoiseDetector(None)
    assert detector.check_for_pattern_noise(data) == False


def test_pattern_noise_does_not_detect_stars(set_random_seed):
    data = 1000 + np.random.normal(0.0, 10.0, size=1000000)
    data = data.reshape(1000, 1000)
    for i in range(5):
        x = np.random.uniform(low=0.0, high=100)
        y = np.random.uniform(low=0.0, high=100)
        brightness = np.random.uniform(low=1000., high=5000.)
        data += gaussian2d(data.shape, x, y, brightness, 3.5)
    detector = pattern_noise.PatternNoiseDetector(None)
    assert detector.check_for_pattern_noise(data) == False


def test_pattern_noise_on_2d_image(set_random_seed):
    data = 100.0 * np.sin(np.arange(1000000) / 0.1) + 1000.0 + np.random.normal(0.0, 10.0, size=1000000)
    data = data.reshape(1000, 1000)

    image = FakeImage()
    image.data = data

    detector = pattern_noise.PatternNoiseDetector(None)
    detector.logger.error = mock.MagicMock()
    detector.do_stage([image])
    assert detector.logger.error.called


def test_trim_edges():
    assert pattern_noise.trim_image_edges(np.zeros((100, 100)), fractional_edge_width=0.25).shape == (50, 50)
    assert pattern_noise.trim_image_edges(np.zeros((100, 100)), fractional_edge_width=0.10).shape == (80, 80)
    assert pattern_noise.trim_image_edges(np.zeros((100, 120)), fractional_edge_width=0.25).shape == (44, 64)


def test_get_2d_power_band(set_random_seed):
    data = np.random.normal(0.0, 10.0, size=(100, 400))
    fft = abs(np.fft.rfft2(data))[37:62, 5:]
    power_band = pattern_noise.get_2d_power_band(data, fractional_band_width=0.25,
                                                 fractional_inner_edge_to_discard=0.025)
    assert power_band.shape == (25, 196)
    np.testing.assert_allclose(power_band, fft)


def test_compute_snr(set_random_seed):
    data = np.random.normal(1000.0, 20.0, size=(500, 100))
    snr = pattern_noise.compute_snr(data)
    assert len(snr) == data.shape[1]-1
    assert all(snr < 5)


def test_get_odd_integer():
    assert pattern_noise.get_odd_integer(1.5) == 3
    assert pattern_noise.get_odd_integer(2) == 3
    assert pattern_noise.get_odd_integer(2.5) == 3


def test_convolve_snr_with_wavelet(set_random_seed):
    snr = (np.sin(np.arange(100) / 5.) + 1) * 2 + np.random.normal(0, 1, 100)
    snr[48:52] = 100
    snr_convolved = pattern_noise.convolve_snr_with_wavelet(snr, nwavelets=25)
    peaks = np.argmax(snr_convolved, axis=1)
    assert snr_convolved.shape == (25, 100)
    assert all(peaks > 48) and all(peaks < 52)


def test_get_peak_parameters_of_single_peak():
    snr_convolved = np.zeros((25, 100))
    snr_convolved[:, 50] = np.arange(25) + 6
    peak_maxima, std_maxima = pattern_noise.get_peak_parameters(snr_convolved)
    assert all(peak_maxima > 5)
    assert std_maxima == 0


def test_get_peak_parameters_of_two_peaks():
    snr_convolved = np.zeros((25, 100))
    snr_convolved[:, 25] = np.arange(25)[::-1] + 6
    snr_convolved[:, 75] = np.arange(25) + 6
    peak_maxima, std_maxima = pattern_noise.get_peak_parameters(snr_convolved)
    assert all(peak_maxima > 5)
    assert std_maxima > 1
