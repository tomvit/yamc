# -*- coding: utf-8 -*-
# @author: Tomas Vitvar, https://vitvar.com, tomas.vitvar@oracle.com

from __future__ import absolute_import
from __future__ import unicode_literals

from dms_collector import DmsCollector
from .provider import BaseProvider

from yamc.utils import Map

class DmsProvider(BaseProvider):
    def __init__(self, config, component_id):
        super().__init__(config, component_id)
        url = self.config.value_str("admin_url", required=True)
        username = self.config.value_str("username")
        password = self.config.value_str("password")
        self.dms = DmsCollector(url, username=username, password=password)
        self.log.info("DMS provider initialized: url=%s, username=%s, password=xxxx"%(url,username))
    
    def table(self,table,include=[],exclude=[],filter=None):
        d = self.dms.collect(table,include=include,exclude=exclude,filter=filter)
        def _add_time(x):
            x["time"]=d["time"]
            return x
        return list(map(_add_time,d["data"]))
        
        
        
