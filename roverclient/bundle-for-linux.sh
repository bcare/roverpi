#!/bin/bash

VERSION=`hg tags | cut -f 1 -d ' ' | tail -n 1`
TIMESTAMP=`date +%Y%m%d`
FILESUFFIX="${VERSION}-${TIMESTAMP}"

pyinstaller --name rvclient-linux --windowed rvclient-linux.spec

if [ ! -d "bundles" ];
then
	mkdir bundles
fi


if (( $? == 0 ));
then
	cd dist
	zip -r ../bundles/rvclient-linux-${FILESUFFIX}.zip  rvclient-linux
	cd ..
fi

pyinstaller --onefile --windowed rvclient-linux-standalone.spec

if (( $?  == 0 ));
then
	cp dist/rvclient-linux-standalone bundles/rvclient-linux-standalone-${FILESUFFIX}.run
fi

