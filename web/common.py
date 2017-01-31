import os
import ConfigParser
import logging
import dateutil.parser
from django.conf import settings
BASE_DIR = settings.BASE_DIR

logger = logging.getLogger(__name__)

def convert_date(date_string):
    try:
        return dateutil.parser.parse(date_string)
    except:
        return date_string

def parse_config():
    config_dict = {}
    config = ConfigParser.ConfigParser(allow_no_value=True)

    conf_path = os.path.join(BASE_DIR, 'mollusc.conf')

    if os.path.exists(conf_path):
        conf_file = conf_path

    else:
        conf_file = '{0}.sample'.format(conf_path)
        logger.warning('Using default config file. Check your mollusc.conf file exists')

    valid = config.read(conf_file)
    if len(valid) > 0:
        config_dict['valid'] = True
        for section in config.sections():
            section_dict = {}
            for key, value in config.items(section):
                section_dict[key] = value
            config_dict[section] = section_dict
    else:
        config_dict['valid'] = False
        logger.error('Unable to find a valid mollusc.conf file.')

    logger.info("Loaded configuration from {0}".format(conf_file))

    return config_dict