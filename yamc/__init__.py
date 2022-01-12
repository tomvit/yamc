# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

from .component import BaseComponent
from .component import WorkerComponent
from .component import PythonExpression

import yamc.writers 
import yamc.collectors
import yamc.providers

from .utils import Map, import_class

__version__ = "1.0.0"

yamc_scope = Map(
    writers=None,
    collectors=None,
    providers=None,
    all_components=[]
)

def load_components(name, config):
    components=Map()
    if config.config.value(name) is None:
        raise Exception("There are no components of type %s"%name)
    for component_id,component_config in config.config.value(name).items():
        try:
            clazz = import_class(component_config["class"])  
            component = clazz(config, component_id)
            if component.enabled:
                components[component_id] = component
        except Exception as e:
            raise Exception("Cannot load component '%s'. %s"%(component_id, str(e)))
    return components

def init_scope(config):
    global yamc_scope
    yamc_scope.writers = load_components("writers", config)
    yamc_scope.collectors=load_components("collectors", config)
    yamc_scope.providers=load_components("providers", config)
    yamc_scope.all_components = list(yamc_scope.writers.values()) + \
        list(yamc_scope.collectors.values()) + list(yamc_scope.providers.values())
    if config.custom_functions is not None:
        for k,v in config.custom_functions.items():
            yamc_scope[k] = v

def start_components(exit_event):
    for component in yamc_scope.all_components:
        if isinstance(component, WorkerComponent):
            component.start(exit_event)
    
def join_components():
    for component in yamc_scope.all_components:
        if isinstance(component, WorkerComponent):
            component.join()

def destroy_components():
    for component in yamc_scope.all_components:
        component.destroy()
                
