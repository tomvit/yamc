# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

import random 
import string
import re

from functools import reduce

class Map(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __getstate__(self):
        return vars(self)

    def __setstate__(self, state):
        vars(self).update(state)

    def __delattr__(self, item):
        self.__delitem__(item)

    def __setitem__(self, key, value):
        super(Map, self).__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delitem__(self, key):
        super(Map, self).__delitem__(key)
        del self.__dict__[key]

    def to_json(self,encoder=None,exclude=[]):
        d = { k:v for k,v in self.__dict__.items() if k not in exclude }        
        return json.dumps(d, skipkeys=True,cls=encoder)

    def update(self,map):
        if isinstance(map, Map):
            self.__dict__.update(map.__dict__)
        if isinstance(map, dict):
            self.__dict__.update(map)

def deep_find(dic, keys, default=None, type=None):
    val=reduce(lambda di,key: di.get(key,default) if isinstance(di, dict) else default, keys.split("."), dic)
    return type(val) if type != None else val 

def import_class(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))    
    
def is_number(s):
    s=str(s)
    p = re.compile(r'^[\+\-]?[0-9]*(\.[0-9]+)?$')
    return s != '' and p.match(s)

