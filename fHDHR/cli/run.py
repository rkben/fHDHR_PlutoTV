import os
import sys
import argparse
import time

from fHDHR import fHDHR_VERSION, fHDHR_OBJ
import fHDHR.exceptions
import fHDHR.config
import fHDHR.logger
from fHDHR.db import fHDHRdb

ERR_CODE = 1
ERR_CODE_NO_RESTART = 2


if sys.version_info.major == 2 or sys.version_info < (3, 7):
    print('Error: fHDHR requires python 3.7+.')
    sys.exit(1)


def build_args_parser():
    """Build argument parser for fHDHR"""
    parser = argparse.ArgumentParser(description='fHDHR')
    parser.add_argument('-c', '--config', dest='cfg', type=str, required=True, help='configuration file to load.')
    return parser.parse_args()


def get_configuration(args, script_dir, plugins, fHDHR_web):
    if not os.path.isfile(args.cfg):
        raise fHDHR.exceptions.ConfigurationNotFound(filename=args.cfg)
    return fHDHR.config.Config(args.cfg, script_dir, plugins, fHDHR_web)


def run(settings, logger, db, script_dir, fHDHR_web, plugins):

    fhdhr = fHDHR_OBJ(settings, logger, db, plugins)
    fhdhrweb = fHDHR_web.fHDHR_HTTP_Server(fhdhr)

    try:

        # Start Flask Thread
        fhdhrweb.start()

        # Start SSDP Thread
        if settings.dict["fhdhr"]["discovery_address"]:
            fhdhr.device.ssdp.start()

        # Start EPG Thread
        if settings.dict["epg"]["method"]:
            fhdhr.device.epg.start()

        # Perform some actions now that HTTP Server is running
        fhdhr.api.get("/api/startup_tasks")

        # wait forever
        restart_code = "restart"
        while fhdhr.threads["flask"].is_alive():
            time.sleep(1)
        return restart_code

    except KeyboardInterrupt:
        return ERR_CODE_NO_RESTART

    return ERR_CODE


def start(args, script_dir, fHDHR_web, plugins):
    """Get Configuration for fHDHR and start"""

    try:
        settings = get_configuration(args, script_dir, plugins, fHDHR_web)
    except fHDHR.exceptions.ConfigurationError as e:
        print(e)
        return ERR_CODE_NO_RESTART

    logger = fHDHR.logger.Logger(settings)

    db = fHDHRdb(settings)

    return run(settings, logger, db, script_dir, fHDHR_web, plugins)


def main(script_dir, fHDHR_web, plugins):
    """fHDHR run script entry point"""

    print("Loading fHDHR %s" % fHDHR_VERSION)
    print("Loading fHDHR_web %s" % fHDHR_web.fHDHR_web_VERSION)

    try:
        args = build_args_parser()
        while True:
            returned_code = start(args, script_dir, fHDHR_web, plugins)
            if returned_code not in ["restart"]:
                return returned_code
    except KeyboardInterrupt:
        print("\n\nInterrupted")
        return ERR_CODE


if __name__ == '__main__':
    main()
