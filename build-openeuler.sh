set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">> 检查并安装依赖..."
yum install -y ca-certificates cmake make gcc gcc-c++ jsoncpp-devel log4cplus-devel re2-devel sqlite-devel tinyxml2-devel

if [ ! -f /usr/include/httplib.h ]; then
    echo ">> 下载 cpp-httplib 头文件..."
    curl -L -o /usr/include/httplib.h https://raw.githubusercontent.com/yhirose/cpp-httplib/master/httplib.h
fi

if [ ! -f /usr/local/lib/libcpp-httplib.a ]; then
    echo ">> 创建 libcpp-httplib.a 占位库..."
    ar rcs /usr/local/lib/libcpp-httplib.a
fi

echo ">> 开始构建..."
cd "$PROJECT_DIR"
rm -rf build && mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)

echo ">> 构建完成。"