""" main.py: Main driver script for PyLCOGT.

    The main() function is a console entry point.

Author
    Curtis McCully (cmccully@lcogt.net)

October 2015
"""
from __future__ import absolute_import, print_function, division

import argparse
import os
from glob import glob

from astropy.io import fits

from pylcogt import bias, dark, flats, trim, photometry, astrometry
from pylcogt import dbs, logs
from pylcogt.images import Image
from pylcogt.utils import file_utils

# A dictionary converting the string input by the user into the corresponding Python object
reduction_stages = [bias.BiasMaker]

logger = logs.get_logger(__name__)
class PipelineContext(object):
    def __init__(self, args):
        self.processed_path = args.processed_path
        self.raw_path = args.raw_path
        self.post_to_archive = args.post_to_archive
        #self.main_query = dbs.generate_initial_query(args)


def get_telescope_info():
    """
    Get information about the available telescopes/instruments from the database.

    Returns
    -------
    all_sites:  list
        List of all site codes, e.g. "lsc".
    all_instruments: list
        List of all instrument code, e.g. "kb78"
    all_telescope_ids: list
        List of all telescope IDs, e.g. "1m0-009"
    all_camera_types: list
        List of available camera types. e.g. "Sinistro" or "SBig"

    Notes
    -----
    The output of this function is used to limit what data is reduced and to validate use input.
"""
    db_session = dbs.get_session()

    all_sites = []
    for site in db_session.query(dbs.Telescope.site).distinct():
        all_sites.append(site[0])

    all_instruments = []
    for instrument in db_session.query(dbs.Telescope.instrument).distinct():
        all_instruments.append(instrument[0])

    all_telescope_ids = []
    for telescope_id in db_session.query(dbs.Telescope.telescope_id).distinct():
        all_telescope_ids.append(telescope_id[0])

    all_camera_types = []
    for camera_type in db_session.query(dbs.Telescope.camera_type).distinct():
        all_camera_types.append(camera_type[0])

    db_session.close()

    return all_sites, all_instruments, all_telescope_ids, all_camera_types


def main(cmd_args=None):
    """
    Main driver script for PyLCOGT. This is a console entry point.
    """
    # Get the available instruments/telescopes
    all_sites, all_instruments, all_telescope_ids, all_camera_types = get_telescope_info()

    parser = argparse.ArgumentParser(description='Reduce LCOGT imaging data.')
    parser.add_argument("--epoch", required=True, type=str, help='Epoch to reduce')
    parser.add_argument("--telescope", default='', choices=all_telescope_ids,
                        help='Telescope ID (e.g. 1m0-010).')
    parser.add_argument("--instrument", default='', type=str, choices=all_instruments,
                        help='Instrument code (e.g. kb74)')
    parser.add_argument("--site", default='', type=str, choices=all_sites,
                        help='Site code (e.g. elp)')
    parser.add_argument("--camera-type", default='', type=str, choices=all_camera_types,
                        help='Camera type (e.g. sbig)')

    parser.add_argument("--raw-path", default='/archive/engineering',
                        help='Top level directory where the raw data is stored')
    parser.add_argument("--processed-path", default='/nethome/supernova/pylcogt',
                        help='Top level directory where the processed data will be stored')

    parser.add_argument("--filter", default='', help="Image filter",
                        choices=['sloan', 'landolt', 'apass', 'up', 'gp', 'rp', 'ip', 'zs',
                                 'U', 'B', 'V', 'R', 'I'])

    parser.add_argument("--binning", default='', choices=['1x1', '2x2'],
                        help="Image binning (CCDSUM)")
    parser.add_argument("--image-type", default='', choices=['BIAS', 'DARK', 'SKYFLAT', 'EXPOSE'],
                        help="Image type to reduce.")

    parser.add_argument("--log-level", default='info', choices=['debug', 'info', 'warning',
                                                                'critical', 'fatal', 'error'])
    parser.add_argument("--ncpus", default=1, type=int,
                        help='Number of multiprocessing cpus to use.')

    parser.add_argument('--db-host', default='mysql+mysqlconnector://cmccully:password@localhost/test')
    parser.add_argument('--post-to-archive', default=False)
    args = parser.parse_args(cmd_args)

    logs.start_logging(log_level=args.log_level)


    stages_to_do = [bias.BiasSubtractor]


    logger = logs.get_logger('Main')
    logger.info('Starting pylcogt:')

    pipeline_context = PipelineContext(args)

    image_list = make_image_list(pipeline_context)
    image_list = select_images(image_list, 'EXPOSE')
    images = read_images(image_list)

    for stage in stages_to_do:
        stage_to_run = reduction_stages[stage](pipeline_context)
        images = stage_to_run.run(images)

    # Save the output images
    save_images(images)

    # Clean up
    logs.stop_logging()

def make_master_bias(cmd_args=None):
    """
    Main driver script for PyLCOGT. This is a console entry point.
    """
    # Get the available instruments/telescopes

    parser = argparse.ArgumentParser(description='Make master calibration frames from LCOGT imaging data.')
    parser.add_argument("--raw-path", default='/archive/engineering',
                        help='Top level directory where the raw data is stored')
    parser.add_argument("--processed-path", default='/nethome/supernova/pylcogt',
                        help='Top level directory where the processed data will be stored')
    parser.add_argument("--log-level", default='info', choices=['debug', 'info', 'warning',
                                                                'critical', 'fatal', 'error'])
    parser.add_argument('--post-to-archive', dest='post_to_archive', action='store_true', default=False)
    parser.add_argument('--db-host', default='mysql+mysqlconnector://cmccully:password@localhost/test')
    args = parser.parse_args(cmd_args)

    logs.start_logging(log_level=args.log_level)

    stages_to_do = [bias.BiasMaker]


    logger.info('Making master calibration frames:')

    pipeline_context = PipelineContext(args)

    image_list = make_image_list(pipeline_context)
    image_list = select_images(image_list, 'BIAS')
    images = read_images(image_list)

    for stage in stages_to_do:
        stage_to_run = stage(pipeline_context)
        images = stage_to_run.run(images)

    master_bias_image = images[0]
    fits.writeto(master_bias_image.filename, master_bias_image.data, header=master_bias_image.header, clobber=True)
    file_utils.post_to_archive_queue(master_bias_image.filename)
    dbs.save_calibration_info('bias', master_bias_image.filename, master_bias_image)
    # Clean up
    logs.stop_logging()


def make_master_dark(cmd_args=None):
    """
    Main driver script for PyLCOGT. This is a console entry point.
    """
    # Get the available instruments/telescopes

    parser = argparse.ArgumentParser(description='Make master calibration frames from LCOGT imaging data.')
    parser.add_argument("--raw-path", default='/archive/engineering',
                        help='Top level directory where the raw data is stored')
    parser.add_argument("--processed-path", default='/nethome/supernova/pylcogt',
                        help='Top level directory where the processed data will be stored')
    parser.add_argument("--log-level", default='info', choices=['debug', 'info', 'warning',
                                                                'critical', 'fatal', 'error'])
    parser.add_argument('--post-to-archive', dest='post_to_archive', action='store_true', default=False)
    parser.add_argument('--db-host', default='mysql+mysqlconnector://cmccully:password@localhost/test')
    args = parser.parse_args(cmd_args)

    logs.start_logging(log_level=args.log_level)

    stages_to_do = [bias.BiasSubtractor, trim.Trimmer, dark.DarkMaker]


    logger.info('Making master calibration frames:')

    pipeline_context = PipelineContext(args)

    image_list = make_image_list(pipeline_context)
    image_list = select_images(image_list, 'DARK')
    images = read_images(image_list)

    for stage in stages_to_do:
        stage_to_run = stage(pipeline_context)
        images = stage_to_run.run(images)

    # Clean up
    logs.stop_logging()


def make_master_flat(cmd_args=None):
    """
    Main driver script for PyLCOGT. This is a console entry point.
    """
    # Get the available instruments/telescopes

    parser = argparse.ArgumentParser(description='Make master calibration frames from LCOGT imaging data.')
    parser.add_argument("--raw-path", default='/archive/engineering',
                        help='Top level directory where the raw data is stored')
    parser.add_argument("--processed-path", default='/nethome/supernova/pylcogt',
                        help='Top level directory where the processed data will be stored')
    parser.add_argument("--log-level", default='info', choices=['debug', 'info', 'warning',
                                                                'critical', 'fatal', 'error'])
    parser.add_argument('--post-to-archive', dest='post_to_archive', action='store_true', default=False)
    parser.add_argument('--db-host', default='mysql+mysqlconnector://cmccully:password@localhost/test')
    args = parser.parse_args(cmd_args)

    logs.start_logging(log_level=args.log_level)

    stages_to_do = [bias.BiasSubtractor, trim.Trimmer, dark.DarkSubtractor, flats.FlatMaker]

    logger.info('Making master flat frames:')

    pipeline_context = PipelineContext(args)

    image_list = make_image_list(pipeline_context)
    image_list = select_images(image_list, 'SKYFLAT')
    images = read_images(image_list)

    for stage in stages_to_do:
        stage_to_run = stage(pipeline_context)
        images = stage_to_run.run(images)

    # Clean up
    logs.stop_logging()


def reduce_science_frames(cmd_args=None):
    """
    Main driver script for PyLCOGT. This is a console entry point.
    """
    # Get the available instruments/telescopes

    parser = argparse.ArgumentParser(description='Make master calibration frames from LCOGT imaging data.')
    parser.add_argument("--raw-path", default='/archive/engineering',
                        help='Top level directory where the raw data is stored')
    parser.add_argument("--processed-path", default='/nethome/supernova/pylcogt',
                        help='Top level directory where the processed data will be stored')
    parser.add_argument("--log-level", default='info', choices=['debug', 'info', 'warning',
                                                               'critical', 'fatal', 'error'])
    parser.add_argument('--post-to-archive', dest='post_to_archive', action='store_true', default=False)
    parser.add_argument('--db-host', default='mysql+mysqlconnector://cmccully:password@localhost/test')
    args = parser.parse_args(cmd_args)

    logs.start_logging(log_level=args.log_level)

    stages_to_do = [bias.BiasSubtractor, trim.Trimmer, dark.DarkSubtractor, flats.FlatDivider,
                    photometry.SourceDetector, astrometry.WCSSolver]

    logger.info('Reducing Science Frames:')

    pipeline_context = PipelineContext(args)

    image_list = make_image_list(pipeline_context)
    image_list = select_images(image_list, 'EXPOSE')
    images = read_images(image_list)
    print(len(images))
    for stage in stages_to_do:
        stage_to_run = stage(pipeline_context)
        images = stage_to_run.run(images)

    save_images(pipeline_context, images)
    # Clean up
    logs.stop_logging()


def read_images(image_list):
    images = []
    for filename in image_list:
        try:
            image = Image(filename)
            images.append(image)
        except Exception as e:
            logger.error(e)
            continue
    return images


def save_images(pipeline_context, images):
    for image in images:
        image_filename = image.header['ORIGNAME'].replace('00.fits', '90.fits')
        filepath = os.path.join(pipeline_context.processed_path, image_filename)
        image.writeto(filepath)
        if pipeline_context.post_to_archive:
            logger.info('Posting {filename} to the archive'.format(filename=image_filename))
            file_utils.post_to_archive_queue(filepath)


def make_image_list(pipeline_context):

    search_path = os.path.join(pipeline_context.raw_path)

    # return the list of file and a dummy image configuration
    return glob(search_path + '/*.fits')


def select_images(image_list, image_type):
    images = []
    for filename in image_list:
        try:
            if fits.getval(filename, 'OBSTYPE') == image_type:
                images.append(filename)
        except Exception as e:
            logger.error(e)
            continue

    return images