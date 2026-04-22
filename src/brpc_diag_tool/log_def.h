#include <string>
namespace brpc {
using namespace std;
// 系统日志
class SystemLog {
public:
    static string logPath;
    string text;
    // int64_t timestamp;
    // ...
};

// Brpc日志
class BrpcLog {
public:
    static string logPath;
    string text;
};
}

/* 
    规范：在本文件中定义日志类，日志类对象可以表示一条日志，也可以进一步封装多条日志。
    日志类对象中可以实现日志检索、字段提取等功能。本样例实现了简单的单条日志定义。
    在类的定义前需要添加对该类表示什么类型的日志的注释，需要和定界文档中“故障现象”字段中对日志来源的描述相对应。  
*/