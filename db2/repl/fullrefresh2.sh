#!/bin/ksh


if [[ $# -lt 3 ]]
  then
    print "Usage: $0 DBName ApplyQual SetName [SetName2...]"
    exit
fi

typeset -u DB AQ SNs

DB="$1"
AQ="$2"
shift 2
SNs="$*"


db2 connect to $DB


for sn in $SNs
  do
    db2 "update asn.ibmsnap_subs_set set synchpoint = NULL, synchtime = current timestamp, lastsuccess = current timestamp, status = 0 where apply_qual = '$AQ' and set_name = '$sn'"
  done


db2 terminate
