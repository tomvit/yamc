# $ yamc

Yet Another Metric Collector (yamc) is a metric collector framework written in Python. It decouples the three main metric collector components namely providers, collectors and writers. Providers provide access to data by means of various access mechanisms and data formats. Writers provide operations to write data to destinations such as DBs or a file system. Collectors call providers' API to retrieve data and writers' API to write the data. They can run on regular intervals or subscribe to providers' events.  

yamc uses a plugin architecture where providers, collectors and writers can be provided by different packages.  

## Development environment setup

In order to setup the development environment for yamc, follow the below steps.

1. Clone the yamc source code to a directory of your choice `${yamc}`.

   ```
   $ git clone https://github.com/tomvit/yamc
   ```

2. Create a Python virtual environment and install required packages. Note that the virtual environment name must be `yamc-env`.
   ```
   $ cd ${yamc}/bin
   $ python3 -m venv yamc-env
   $ source ./evn.sh
   $ pip install -r requirements-base.txt
   ```

3. (optional) If you are using yamc plugins for the Oracle DB and `dms-collector`, you will also need to install the required packages as follows.

   ```
   $ pip install -r requirements-oracle.txt
   ```  

   In addition, enable the Oracle yamc plugins in `${yamc}/bin/env.sh` by uncommenting the corresponding lines with `PYTHONPATH` environment variable that specify location of the plugins. You will then need to load the `env.sh` again.


4. Run `yamc` command line.

   ```
   $ yamc --help
   usage: yamc [-h] --config <file> [--env <file>] [--test]  
   [--show-config] [--debug | --trace]

   Yet another metric collector

   optional arguments:
     -h, --help       show this help message and exit

   required arguments:
     --config <file>  Configuration file

   other optional arguments:
     --env <file>     Environment variables file
     --test           Run in the test mode with disabled writing activities
     --show-config    Show consolidated configuration before validation
     --debug          Print debug details in the log
     --trace          Print even more details in the log
   ```

5. Create toyr configuration file in `${yamc}/config` directory and an environment variable file if your configuration is parametrized. Run the yamc server as follows.

   ```
   $ yamc --config config/mqtt-config.yaml
   ```
