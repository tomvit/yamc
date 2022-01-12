#!/bin/bash
mdir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../.. && pwd )

. $mdir/yamc/bin/yamc-env/bin/activate 

export PATH=$PATH:$mdir/yamc/bin

export PYTHONPATH=$mdir/yamc
export PYTHONPATH=$PYTHONPATH:$mdir/dms-collector
export PYTHONPATH=$PYTHONPATH:$mdir/yamc/plugins/yamc-oracle
