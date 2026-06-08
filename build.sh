#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Removing build directory..."
rm -rf build

echo "Creating build directory..."
mkdir build

echo "Entering build directory and running cmake..."
cd build

cmake .. \
  -DCMAKE_C_COMPILER=/usr/local/opt/llvm/bin/clang \
  -DCMAKE_CXX_COMPILER=/usr/local/opt/llvm/bin/clang++ \
  -DCMAKE_CXX_STANDARD=17 \
  -DCMAKE_CXX_STANDARD_REQUIRED=ON \
  -DCMAKE_CXX_FLAGS="-DHOST_NAME_MAX=255" \
  -DOPENSSL_ROOT_DIR=/usr/local/opt/openssl@3 \
  -DOPENSSL_INCLUDE_DIR=/usr/local/opt/openssl@3/include \
  -DOPENSSL_CRYPTO_LIBRARY=/usr/local/opt/openssl@3/lib/libcrypto.dylib \
  -DOPENSSL_SSL_LIBRARY=/usr/local/opt/openssl@3/lib/libssl.dylib \
  -DCMAKE_EXE_LINKER_FLAGS="-L/usr/local/lib -llog4cplus"

echo "Running make..."
make -j$(sysctl -n hw.ncpu)

echo "Build completed successfully!"
