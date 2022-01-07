#!/bin/bash
mdir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../.. && pwd )

export PYTHONPATH=$PYTHONPATH:$mdir/yamc
export PYTHONPATH=$PYTHONPATH:$mdir/dms-collector
