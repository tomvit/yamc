# Yet Another Metric Collector

yamc is a metric collector framework writen in Python. It decouples the three main metric collector components namely providers, collectors and writers. Providers provide access to data by means of various access mechanisms and data formats. Writers provide operations to write data to destinations such as DBs or a file system. Collectors run in regular intervals, they call providers' API to retrieve data and writers' API to write the data. 

yamc uses a plugin architecture where providers, collectors and writers can be provided by different packages.  

