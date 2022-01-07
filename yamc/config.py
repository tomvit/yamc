# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import os
import sys
import yaml
import logging 
import logging.config
import re
import warnings

warnings.filterwarnings("ignore",category=DeprecationWarning)

import imp 

from yamc import PythonExpression
from .utils import deep_find, import_class, Map

# matcher and resolver to resolve environment variables to values in YAML
def py_constructor(loader, node):
    try:
        return PythonExpression(node.value)
    except Exception as e:
        print(node)
        raise Exception("Cannot create python expression from string \"%s\". The error was: %s"%(node.value,str(e)))

# register resolver with YAML parser
yaml.add_constructor('!py', py_constructor)

class Config():
    def __init__(self, file, args):
        self.collectors = {}
        self.writers = {}
        self.providers = {}
        self.args = args
        
        if not(os.path.exists(file)):
            raise Exception("The configuration file %s does not exist!"%file)
        
        self.config_file=os.path.realpath(file)
        self.config_dir=os.path.dirname(self.config_file)
        stream = open(self.config_file, encoding="utf-8")
        try:
            self.config=ConfigPart(None, yaml.load(stream, Loader=yaml.FullLoader))
        except Exception as e:
            raise Exception("Error when reading the configuration file %s: %s"%(file,str(e)))
        finally:
            stream.close()

        self.logs_dir = self.get_dir_path(self.config.value("directories.logs", default="../logs"))
        self.data_dir = self.get_dir_path(self.config.value("directories.data", default="../data"))
        os.makedirs(self.logs_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        addLoggingLevel('TRACE', logging.DEBUG - 5)
        self.log_level = "DEBUG" if args.debug else "INFO" 
        
        log_handlers = ['file','console']
        if self.args.test:
            log_handlers = ['console']
        
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': True,
            'formatters': { 
                'standard': { 
                    'format': '%(asctime)s [%(name)-10.10s] [%(levelname)-1.1s] %(message)s',
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },        
            },
            'handlers': { 
                'console': { 
                    'formatter': 'standard',
                    'class': 'logging.StreamHandler',
                    'stream': 'ext://sys.stdout',  # Default is stderr
                },
                'file': { 
                    'formatter': 'standard',
                    'class': 'logging.handlers.TimedRotatingFileHandler',
                    'filename': f'{self.logs_dir}/yamc.log',
                    'when': 'midnight',
                    'interval': 1,
                    'backupCount': 30
                },                        
            },
            'loggers': { 
                '': {  # all loggers
                    'handlers': log_handlers,
                    'level': f'{self.log_level}',
                    'propagate': False
                }
            } 
        })
        
        self.log = logging.getLogger('config')
        
        if self.args.test:
            self.log.info("Running in test mode, the log output will be in console only.")
        
        # load custom functions if they exist
        from inspect import getmembers, isfunction
        self.custom_functions = {}
        for name,file in self.config.value("custom-functions", default={}).items():
            filename = self.get_dir_path(file, check=True)
            directory = os.path.dirname(filename)
            modulename = re.sub(r'\.py$',"", os.path.basename(filename))
            self.log.debug("Importing custom module with id %s: module=%s, directory=%s"%(name,modulename,directory))
            fp, path, desc = imp.find_module(modulename, [directory])
            module = imp.load_module(modulename,fp,path,desc)
            self.custom_functions[name] = Map({x[0]:x[1] for x in getmembers(module, isfunction)})

    def get_dir_path(self, path, base_dir=None, check=False):
        d=os.path.normpath((((self.config_dir if base_dir is None else base_dir) + '/') if path[0]!='/' else '') + path)
        if check and not os.path.exists(d):
            raise Exception(f"The directory {d} does not exist, you need to create it!")
        return d
    
    def collector(self,collector_id):
        if collector_id not in self.collectors:
            self.collectors[collector_id] = ConfigPart("collectors.%s"%collector_id, self.config._config)
        return self.collectors[collector_id]

    def writer(self,writer_id):
        if writer_id not in self.writers:
            self.writers[writer_id] = ConfigPart("writers.%s"%writer_id, self.config._config)
        return self.writers[writer_id]

    def provider(self,provider_id):
        if provider_id not in self.providers:
            self.providers[provider_id] = ConfigPart("providers.%s"%provider_id, self.config._config)
        return self.providers[provider_id]

    def exists(self, path):
        return deep_find(self.config._config, path) is not None

class ConfigPart():
    def __init__(self, base_path, config):
        self.base_path = base_path
        if base_path is not None:
            self._config = deep_find(config, base_path)
        else:
            self._config = config

    def path(self, path):
        return "%s.%s"%(self.base_path,path) if self.base_path is not None else path

    def value(self, path, default=None, type=None, raise_ex=True):
        if self._config is not None:
            return deep_find(self._config, path, default, type)    
        else:
            if raise_ex:
                raise Exception("The property %s does not exist!"%(self.path(path)))
            else:
                return default
                
    def value_str(self, path, default=None, regex=None, required=False):
        v = self.value(path, default=default, type=str, raise_ex=required)
        if regex is not None and not re.match(regex, v):
            raise Exception("The property %s value %s does not match %s!"%(self.path(path), v, regex))
        return v
        
    def value_int(self, path, default=None, min=None, max=None, required=False):
        v = self.value(path, default=default, type=int, raise_ex=required)
        if min is not None and v < min:
            raise Exception("The property %s value %s must be greater or equal to %d!"%(self.path(path), min))
        if max is not None and v > max:
            raise Exception("The property %s value %s must be less or equal to %d!"%(self.path(path), max))            
        return v

    def value_bool(self, path, default=None, required=False):
        return self.value(path, default=default, type=bool, raise_ex=required)
    
# from https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/35804945#35804945
def addLoggingLevel(levelName, levelNum, methodName=None):
    '''
    Comprehensively adds a new logging level to the `logging` module and the
    currently configured logging class.

    `levelName` becomes an attribute of the `logging` module with the value
    `levelNum`. `methodName` becomes a convenience method for both `logging`
    itself and the class returned by `logging.getLoggerClass()` (usually just
    `logging.Logger`). If `methodName` is not specified, `levelName.lower()` is
    used.

    To avoid accidental clobberings of existing attributes, this method will
    raise an `AttributeError` if the level name is already an attribute of the
    `logging` module or if the method name is already present 

    Example
    -------
    >>> addLoggingLevel('TRACE', logging.DEBUG - 5)
    >>> logging.getLogger(__name__).setLevel("TRACE")
    >>> logging.getLogger(__name__).trace('that worked')
    >>> logging.trace('so did this')
    >>> logging.TRACE
    5
    '''
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
       raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
       raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
       raise AttributeError('{} already defined in logger class'.format(methodName))

    # This method was inspired by the answers to Stack Overflow post
    # http://stackoverflow.com/q/2183233/2988730, especially
    # http://stackoverflow.com/a/13638084/2988730
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)