#!/bin/bash

tmpdir=$(mktemp -d)
outputdir=$(pwd)/_build

rm -rf $outputdir
mkdir -p $outputdir

cp -r . $tmpdir/vmlight

pushd $tmpdir/vmlight

# Build the package
dpkg-buildpackage -us -uc

popd

# Move build artifacts to our custom directory
find $tmpdir -maxdepth 1 -name "vmlight_*" -type f -exec mv {} $outputdir/ \;

rm -rf $tmpdir
