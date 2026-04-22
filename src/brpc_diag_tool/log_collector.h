#include "log_def.h"
#include <string>

namespace brpc {
using namespace std;
class LogCollector {
public:
    vector<SystemLog> CollectSystemLog(int64_t timestamp);
    vector<BrpcLog> CollectBrpcLog(int64_t timestamp);
};
}

/*
    规范：在本文件中定义日志采集的实现逻辑。本样例实现了从系统日志和brpc日志样例中分别读取日志数据的功能。
*/