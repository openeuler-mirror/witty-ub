#ifndef FAILURE_LOG_INFO_H
#define FAILURE_LOG_INFO_H

#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace diag {
enum class LevelOption {
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
    std::string failureModeId;
    std::string rawLog;

    bool operator==(const FailureLogInfo &other) const
    {
        return timestamp == other.timestamp && level == other.level && filename == other.filename &&
               lineNo == other.lineNo && podName == other.podName && pid == other.pid && tid == other.tid &&
               traceId == other.traceId && clusterName == other.clusterName && message == other.message &&
               rawLog == other.rawLog;
    }
};
} // namespace diag

#endif