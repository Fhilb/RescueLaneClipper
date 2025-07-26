#!/bin/bash

# Exit on any error
set -e

# Define version and URL
TUSD_VERSION="v2.8.0"
TUSD_ARCHIVE="tusd_linux_arm.tar.gz"
TUSD_URL="https://github.com/tus/tusd/releases/download/$TUSD_VERSION/$TUSD_ARCHIVE"
TUSD_DIR="tusd_linux_arm"

echo "Downloading tusd version $TUSD_VERSION..."
wget $TUSD_URL

echo "Extracting archive..."
tar -xzf $TUSD_ARCHIVE

echo "Changing directory to extracted folder..."
cd $TUSD_DIR

echo "Setting executable permissions on tusd binary..."
chmod +x tusd

echo "Moving tusd binary to /usr/local/bin (requires sudo)..."
sudo mv tusd /usr/local/bin/

echo "Creating upload directory..."
mkdir -p ~/tus-uploads

echo "Verifying installation..."
TUSD_PATH=$(which tusd)
TUSD_VERSION_OUTPUT=$(tusd -version)

echo "Binary location: $TUSD_PATH"
echo "Version output:"
echo "$TUSD_VERSION_OUTPUT"

cd ..
echo "Cleaning up..."
rm -rf $TUSD_DIR*
echo "Done."
