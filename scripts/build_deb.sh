#!/bin/bash

tmpdir=$(mktemp -d)
outputdir=$(pwd)/_build

rm -rf $outputdir
mkdir -p $outputdir

cp -r . $tmpdir/vmlight

pushd $tmpdir/vmlight

# Update the changelog with the current date
curdate=$(date -R) envsubst < debian/changelog > debian/changelog.tmp
mv debian/changelog.tmp debian/changelog

# Build the package
dpkg-buildpackage -us -uc

popd

# Move build artifacts to our custom directory
find $tmpdir -maxdepth 1 -name "vmlight_*" -type f -exec mv {} $outputdir/ \;

rm -rf $tmpdir
