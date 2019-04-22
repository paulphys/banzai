import hashlib
import os
import logging

from kombu import Connection, Exchange

logger = logging.getLogger(__name__)


def post_to_archive_queue(image_path):
    exchange = Exchange('fits_files', type='fanout')
    with Connection('amqp://guest:guest@rabbitmq.lco.gtn:5672//?heartbeat=10') as conn:
        producer = conn.Producer(exchange=exchange)
        producer.publish({'path': image_path})
        producer.release()


def make_output_directory(runtime_context, image_config):
    # Create output directory if necessary
    output_directory = os.path.join(runtime_context.processed_path, image_config.site,
                                    image_config.camera, image_config.epoch)

    if runtime_context.preview_mode:
        output_directory = os.path.join(output_directory, 'preview')
    else:
        output_directory = os.path.join(output_directory, 'processed')

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    return output_directory


def get_md5(filepath):
    with open(filepath, 'rb') as file:
        md5 = hashlib.md5(file.read()).hexdigest()
    return md5


def instantly_public(proposal_id):
    public_now = False
    if proposal_id in ['calibrate', 'standard', 'pointing']:
        public_now = True
    if 'epo' in proposal_id.lower():
        public_now = True
    return public_now


def ccdsum_to_filename(image):
    return 'bin{ccdsum}'.format(ccdsum=image.ccdsum.replace(' ', 'x'))


def filter_to_filename(image):
    return str(image.filter)


def config_to_filename(image):
    filename = str(image.configuration_mode)
    filename = filename.replace('full_frame', 'full')
    filename = filename.replace('central_2k_2x2', 'center')
    return filename
