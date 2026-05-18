#ifndef FAILURE_LOG_INFO_H
#define FAILURE_LOG_INFO_H

#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace diag {
enum LevelOption {
    INFO,
    DEBUG,
    WARN,
    ERROR
};

struct FailureLogInfo {
    int64_t timestamp;
    LevelOption level;
    std::string filename;
    int lineNo;
    std::string podName;
    int pid;
    int tid;
    std::string traceId;
    std::string clusterName;
    std::string message;

    std::string failureModeId; // 该日志对应的故障模式ID
};
} // namespace diag

#endif