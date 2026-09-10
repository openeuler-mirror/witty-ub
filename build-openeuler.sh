set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">> Checking and installing dependencies..."
yum install -y ca-certificates cmake make gcc gcc-c++ jsoncpp-devel log4cplus-devel re2-devel sqlite-devel tinyxml2-devel

if [ ! -f /usr/include/httplib.h ]; then
    echo ">> Downloading the cpp-httplib header..."
    curl -L -o /usr/include/httplib.h https://raw.githubusercontent.com/yhirose/cpp-httplib/master/httplib.h
fi

if [ ! -f /usr/local/lib/libcpp-httplib.a ]; then
    echo ">> Creating the libcpp-httplib.a placeholder library..."
    ar rcs /usr/local/lib/libcpp-httplib.a
fi

echo ">> Building..."
cd "$PROJECT_DIR"
rm -rf build && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

echo ">> Build completed."
