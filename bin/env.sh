#!/bin/bash
bdir=$(realpath)
mdir=$( cd $bdir && cd ../.. && pwd)

if [ ! -f $bdir/yamc-env/bin/activate ]; then
  echo "ERROR: You must source the env.sh script from the yamc/bin directory and the Python virtual environment must exist!"
else 
  . $bdir/yamc-env/bin/activate 
  export PATH=$PATH:$mdir/yamc/bin
  export PYTHONPATH=$mdir/yamc

  # plugins 
  export PYTHONPATH=$PYTHONPATH:$mdir/yamc/plugins/yamc-mqtt
  export PYTHONPATH=$PYTHONPATH:$mdir/yamc/plugins/yamc-pushover
  #export PYTHONPATH=$PYTHONPATH:$mdir/dms-collector
  #export PYTHONPATH=$PYTHONPATH:$mdir/yamc/plugins/yamc-oracle
fi
