# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas@vitvar.com

from __future__ import absolute_import
from __future__ import unicode_literals

import os
import sys
import yaml
import logging
import logging.config
import re
import warnings
import json

warnings.filterwarnings("ignore", category=DeprecationWarning)

import imp

from .utils import PythonExpression
from .utils import deep_find, import_class, Map, deep_merge, merge_dicts
from functools import reduce
from yamc import yamc_scope

# they must be in a form ${VARIABLE_NAME}
ENVNAME_PATTERN = "[A-Z0-9_]+"
ENVPARAM_PATTERN = "\$\{%s\}" % ENVNAME_PATTERN

# consolidated variables supplied via env file and environment variables
ENV = {}


def get_dir_path(config_dir, path, base_dir=None, check=False):
    """
    Returns the directory for the path specified.
    """
    d = os.path.normpath(
        (
            ((config_dir if base_dir is None else base_dir) + "/")
            if path[0] != "/"
            else ""
        )
        + path
    )
    if check and not os.path.exists(d):
        raise Exception(f"The directory {d} does not exist!")
    return d


def read_raw_config(config_file, env_file):
    """
    Reads the raw configuration file by processing config `include` instructions and
    populating `defaults` to `providers`, `collectors` and `writers`. This is a wrapper function
    for the function `read_complex_config`.
    """
    if not (os.path.exists(config_file)):
        raise Exception(f"The configuration file {config_file} does not exist!")
    if env_file and not (os.path.exists(env_file)):
        raise Exception(f"The environment file {env_file} does not exist!")

    # init yaml reader
    global ENV
    ENV = init_env(env_file)
    yaml.add_implicit_resolver("!env", re.compile(r".*%s.*" % ENVPARAM_PATTERN))
    yaml.add_constructor("!env", env_constructor)
    yaml.add_constructor("!py", py_constructor)

    # read configuration
    config, config_file = read_complex_config(config_file)
    config_dir = os.path.dirname(config_file)

    # add defaults
    add_defaults(config, "collectors")
    add_defaults(config, "providers")
    add_defaults(config, "writers")

    return config, config_file, config_dir


def read_complex_config(file):
    """
    Reads complex configuration file by processing `include` instructions.
    """

    def _read_yaml(config_file):
        stream = open(config_file, encoding="utf-8")
        try:
            return yaml.load(stream, Loader=yaml.FullLoader)
        except Exception as e:
            raise Exception(
                f"Error when reading the configuration file {file}: {str(e)}"
            )
        finally:
            stream.close()

    def _traverse(config_dir, d):
        if isinstance(d, dict):
            result = {}
            for k, v in d.items():
                if k == "include" and isinstance(v, list):
                    for f in v:
                        result = deep_merge(
                            result, read_complex_config(get_dir_path(config_dir, f))[0]
                        )
                elif isinstance(v, dict):
                    result[k] = _traverse(config_dir, v)
                else:
                    result[k] = v
            return result
        else:
            return d

    config_file = os.path.realpath(file)
    config = _read_yaml(config_file)
    return _traverse(os.path.dirname(config_file), config), config_file


def add_defaults(config, component_name):
    """
    Adds defaults settings to individual `providers`, `collectors` and `writers`.
    """
    collectors_defaults = deep_find(config, f"defaults.{component_name}", default=[])
    for cdef in collectors_defaults:
        for k, v in config.get(component_name, {}).items():
            if re.search(cdef.get("pattern"), k):
                for k1, v1 in cdef.items():
                    if k1 != "pattern":
                        if k1 not in v.keys():
                            v[k1] = v1
    return config


def init_env(env_file, sep="=", comment="#"):
    """
    Reads environment varialbes from the `env_file` and combines them with the OS environment variables.
    """
    env = {}
    for k, v in os.environ.items():
        env[k] = v
    if env_file:
        with open(env_file, "rt") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith(comment):
                    key_value = l.split(sep)
                    key = key_value[0].strip()
                    if not re.match(f"^{ENVNAME_PATTERN}$", key):
                        raise Exception(f"Invalid variable name '{key}'.")
                    value = sep.join(key_value[1:]).strip().strip("\"'")
                    env[key] = value
    return env


def replace_env_variable(value):
    params = list(set(re.findall("(%s)" % ENVPARAM_PATTERN, value)))
    if len(params) > 0:
        for k in params:
            env_value = ENV.get(k[2:-1])
            if env_value is None:
                raise Exception(f"The environment variable {k} does not exist!")
            else:
                value = value.replace(k, env_value)
    return value


def env_constructor(loader, node):
    """
    A constructor for environment varaibles provided in the yaml configuration file.
    It populates strings that contain environment variables in a form `${var_name}` with
    their values.
    """
    return replace_env_variable(node.value)


def py_constructor(loader, node):
    """
    A constructor for Python expression in the yaml configuration file. The python expression
    must be prefixed by `!py` directive. The result is the `PythonExpression` object.
    """
    try:
        return PythonExpression(replace_env_variable(node.value))
    except Exception as e:
        raise Exception(
            'Cannot create python expression from string "%s". %s'
            % (node.value, str(e))
        )


class Config:
    """
    The main yamc confuguration. It reads the configuration from the yaml file, initializes logging,
    loads custom functions' modules and provides methods to access individual `providers`,
    `collectors` and `writers` configurations.
    """

    def __init__(self, file, args):
        """
        Reads and parses the configuration from the yaml file and initializes the logging.
        """
        self.collectors = {}
        self.writers = {}
        self.providers = {}
        self.args = args

        if not (os.path.exists(file)):
            raise Exception(f"The configuration file {file} does not exist!")

        self.raw_config, self.config_file, self.config_dir = read_raw_config(
            self.args.config, self.args.env
        )
        self.logs_dir, self.logs_level = self.init_logging(
            deep_find(self.raw_config, "directories.logs", default="../logs")
        )
        self.log = logging.getLogger("config")

    def init_config(self):
        """
        Creates the main configuration object and loads the custom functions' modules.
        """
        self.config = ConfigPart(None, None, self.raw_config, self.config_dir)
        self.data_dir = self.get_dir_path(
            self.config.value("directories.data", default="../data")
        )
        os.makedirs(self.data_dir, exist_ok=True)

        if self.args.test:
            self.log.info(
                "Running in test mode, the log output will be in console only."
            )

        # load custom functions if they exist
        from inspect import getmembers, isfunction

        self.custom_functions = {}
        for name, file in self.config.value("custom-functions", default={}).items():
            filename = self.get_dir_path(file, check=True)
            directory = os.path.dirname(filename)
            modulename = re.sub(r"\.py$", "", os.path.basename(filename))
            self.log.debug(
                "Importing custom module with id %s: module=%s, directory=%s"
                % (name, modulename, directory)
            )
            fp, path, desc = imp.find_module(modulename, [directory])
            module = imp.load_module(modulename, fp, path, desc)
            self.custom_functions[name] = Map(
                {x[0]: x[1] for x in getmembers(module, isfunction)}
            )

    def init_logging(self, logs_dir):
        """
        Initializes the logging, sets the log level and logging directory. It also
        adds a custom 'TRACE' logging level.
        """
        # custom TRACE logging level
        addLoggingLevel("TRACE", logging.DEBUG - 5)

        # logs directory
        logs_dir = self.get_dir_path(logs_dir)
        os.makedirs(logs_dir, exist_ok=True)

        # log level
        log_level = "INFO"
        if self.args.trace:
            log_level = "TRACE"
        elif self.args.debug:
            log_level = "DEBUG"

        # log handlers
        log_handlers = ["file", "console"]
        if self.args.test:
            log_handlers = ["console"]

        # main logs configuration
        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": True,
                "formatters": {
                    "standard": {
                        "format": ColoredFormatter.format_header
                        + ColoredFormatter.format_msg
                    },
                    "colored": {"()": ColoredFormatter},
                },
                "handlers": {
                    "console": {
                        "formatter": "colored",
                        "class": "logging.StreamHandler",
                        "stream": "ext://sys.stdout",  # Default is stderr
                    },
                    "file": {
                        "formatter": "standard",
                        "class": "logging.handlers.TimedRotatingFileHandler",
                        "filename": f"{logs_dir}/yamc.log",
                        "when": "midnight",
                        "interval": 1,
                        "backupCount": 30,
                    },
                },
                "loggers": {
                    "": {  # all loggers
                        "handlers": log_handlers,
                        "level": f"{log_level}",
                        "propagate": False,
                    }
                },
            }
        )
        return logs_dir, log_level

    def get_dir_path(self, path, base_dir=None, check=False):
        """
        Returns the full directory of the path with `config_dir` as the base directory.
        """
        return get_dir_path(self.config_dir, path, base_dir, check)

    def collector(self, collector_id):
        """
        Returns a `ConfigPart` object for a collector with `collector_id`
        """
        if collector_id not in self.collectors:
            self.collectors[collector_id] = ConfigPart(
                self,
                "collectors.%s" % collector_id,
                self.config._config,
                self.config_dir,
            )
        return self.collectors[collector_id]

    def writer(self, writer_id):
        """
        Returns a `ConfigPart` object for a writer with `writer_id`
        """
        if writer_id not in self.writers:
            self.writers[writer_id] = ConfigPart(
                self, "writers.%s" % writer_id, self.config._config, self.config_dir
            )
        return self.writers[writer_id]

    def provider(self, provider_id):
        """
        Returns a `ConfigPart` object for a provider with `provider_id`
        """
        if provider_id not in self.providers:
            self.providers[provider_id] = ConfigPart(
                self, "providers.%s" % provider_id, self.config._config, self.config_dir
            )
        return self.providers[provider_id]


class ConfigPart:
    def __init__(self, parent, base_path, config, config_dir):
        self.parent = parent
        self.config_dir = config_dir
        self.base_path = base_path
        if base_path is not None:
            self._config = deep_find(config, base_path)
        else:
            self._config = config

    def get_dir_path(self, path, base_dir=None, check=False):
        return get_dir_path(self.config_dir, path, base_dir, check)

    def path(self, path):
        return "%s.%s" % (self.base_path, path) if self.base_path is not None else path

    def value(self, path, default=None, type=None, required=True, no_eval=False):
        required = default is not None and required
        r = default
        if self._config is not None:
            val = reduce(
                lambda di, key: di.get(key, default)
                if isinstance(di, dict)
                else default,
                path.split("."),
                self._config,
            )
            if val == default:
                r = default
            else:
                if not no_eval:
                    if callable(getattr(val, "eval", None)):
                        try:
                            from yamc import yamc_scope

                            val = val.eval(
                                merge_dicts(self.parent.custom_functions, yamc_scope)
                            )
                        except Exception as e:
                            raise Exception(
                                "Cannot evaluate Python expression for property '%s'. %s"
                                % (self.path(path), str(e))
                            )
                r = type(val) if type != None else val
        if not r and required:
            raise Exception("The property '%s' does not exist!" % (self.path(path)))
        return r

    def value_str(self, path, default=None, regex=None, required=False):
        v = self.value(path, default=default, type=str, required=required)
        if regex is not None and not re.match(regex, v):
            raise Exception(
                "The property %s value %s does not match %s!"
                % (self.path(path), v, regex)
            )
        return v

    def value_int(self, path, default=None, min=None, max=None, required=False):
        v = self.value(path, default=default, type=int, required=required)
        if min is not None and v < min:
            raise Exception(
                "The property %s value %s must be greater or equal to %d!"
                % (self.path(path), min)
            )
        if max is not None and v > max:
            raise Exception(
                "The property %s value %s must be less or equal to %d!"
                % (self.path(path), max)
            )
        return v

    def value_bool(self, path, default=None, required=False):
        return self.value(path, default=default, type=bool, required=required)


class ColoredFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_header = "%(asctime)s [%(name)-10.10s] "
    format_msg = "[%(levelname)-1.1s] %(message)s"

    FORMATS = {
        logging.DEBUG: format_header + grey + format_msg + reset,
        logging.INFO: format_header + grey + format_msg + reset,
        logging.WARNING: format_header + yellow + format_msg + reset,
        logging.ERROR: format_header + red + format_msg + reset,
        logging.CRITICAL: format_header + bold_red + format_msg + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


# from https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/35804945#35804945
def addLoggingLevel(levelName, levelNum, methodName=None):
    """
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
    """
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

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
