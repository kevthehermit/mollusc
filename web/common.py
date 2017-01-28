import os
import ConfigParser
import logging
import dateutil.parser

logger = logging.getLogger(__name__)

def convert_date(date_string):
    try:
        return dateutil.parser.parse(date_string)
    except:
        return date_string

def parse_config():
    config_dict = {}
    config = ConfigParser.ConfigParser(allow_no_value=True)

    if os.path.exists('mollusc.conf'):
        conf_file = 'mollusc.conf'

    else:
        conf_file = 'mollusc.conf.sample'
        logger.warning('Using default config file. Check your mollusc.conf.conf file exists')

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
        logger.error('Unable to find a valid volutility.conf file.')

    logger.info("Loaded configuration from {0}".format(conf_file))

    return config_dict