"""
settings.py: Settings script for banzai.

    Important note: due to the way that the parameters are read in,
    variables that begin with an underscore will not be added to the
    pipeline context.

"""
import operator
import abc

from banzai.context import InstrumentCriterion
from banzai import qc, bias, crosstalk, gain, mosaic, bpm, trim, dark, flats, photometry, astrometry, images
from banzai.utils.file_utils import ccdsum_to_filename, filter_to_filename
from banzai.calibrations import make_calibration_filename_function


def telescope_to_filename(image):
    return image.header.get('TELESCOP', '').replace('-', '')


SCHEDULABLE_CRITERIA = [InstrumentCriterion('schedulable', operator.eq, True)]

FRAME_SELECTION_CRITERIA = [InstrumentCriterion('type', operator.contains, 'FLOYDS', exclude=True),
                            InstrumentCriterion('type', operator.contains, 'NRES', exclude=True)]

FRAME_CLASS = images.Image

ORDERED_STAGES = [bpm.BPMUpdater,
                  qc.HeaderSanity,
                  qc.ThousandsTest,
                  qc.SaturationTest,
                  bias.OverscanSubtractor,
                  crosstalk.CrosstalkCorrector,
                  gain.GainNormalizer,
                  mosaic.MosaicCreator,
                  trim.Trimmer,
                  bias.BiasSubtractor,
                  dark.DarkSubtractor,
                  flats.FlatDivider,
                  qc.PatternNoiseDetector,
                  photometry.SourceDetector,
                  astrometry.WCSSolver,
                  qc.pointing.PointingTest]

CALIBRATION_MIN_FRAMES = {'BIAS': 5,
                          'DARK': 5,
                          'SKYFLAT': 5}

CALIBRATION_SET_CRITERIA = {'BIAS': ['ccdsum'],
                            'DARK': ['ccdsum'],
                            'SKYFLAT': ['ccdsum', 'filter']}

LAST_STAGE = {'BIAS': trim.Trimmer, 'DARK': bias.BiasSubtractor, 'SKYFLAT': dark.DarkSubtractor,
              'SINISTRO': mosaic.MosaicCreator, 'STANDARD': None, 'EXPOSE': None}

EXTRA_STAGES = {'BIAS': [bias.BiasMasterLevelSubtractor, bias.BiasComparer],
                'DARK': [dark.DarkNormalizer, dark.DarkComparer],
                'SKYFLAT': [flats.FlatNormalizer, qc.PatternNoiseDetector, flats.FlatComparer],
                'STANDARD': None,
                'EXPOSE': None}

CALIBRATION_STACKER_STAGE = {'BIAS': bias.BiasMaker,
                             'DARK': dark.DarkMaker,
                             'SKYFLAT': flats.FlatMaker}

CALIBRATION_IMAGE_TYPES = ['BIAS', 'DARK', 'SKYFLAT']

SINISTRO_IMAGE_TYPES = ['BIAS', 'DARK', 'SKYFLAT', 'EXPOSE', 'STANDARD', 'TRAILED', 'EXPERIMENTAL']

CALIBRATION_FILENAME_FUNCTIONS = {'BIAS': make_calibration_filename_function('BIAS', [ccdsum_to_filename], telescope_to_filename),
                                  'DARK': make_calibration_filename_function('DARK', [ccdsum_to_filename], telescope_to_filename),
                                  'SKYFLAT': make_calibration_filename_function('SKYFLAT', [ccdsum_to_filename, filter_to_filename],
                                                                                telescope_to_filename)}