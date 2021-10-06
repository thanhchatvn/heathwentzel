# -*- coding: utf-8 -*-


import logging

_logger = logging.getLogger(__name__)

HAS_WDB = False

try:
    import wdb
    HAS_WDB = True
except:
    _logger.info('Unable to import wdb; if you really need to debug, consider installing it.')

def _SET_TRACE():
    _logger.info("HAS_WDB {0}".format(HAS_WDB))
    if HAS_WDB:
        wdb.set_trace()

_set_trace = _SET_TRACE

from . import models
from . import report
from . import wizard
