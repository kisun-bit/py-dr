#!/bin/bash

echo "$0 $1"

cd dist

dist_name=clw-config-service-client-$1.zip

echo $dist_name

if [ ! -f $dist_name ]; then
  echo "******** not exist $dist_name ********"
  exit 1
fi

scp $dist_name 172.16.1.65:/root/packages/

if [ $? -ne 0 ]  
then  
  echo "******** scp $dist_name failed ********"
  exit 1
fi

cd ..