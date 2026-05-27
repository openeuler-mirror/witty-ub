#pragma once

#include <string>
#include <vector>

#include "../../failure_log_info.h"

namespace diag {
namespace urma_log_helper {

std::string RunCommand(const std::string &cmd);
bool ParseFailureLogLine(const std::string &line, FailureLogInfo &logInfo);
const std::vector<FailureLogInfo> &GetParsedFailureLogLines(const FailureLogInfo &logInfo);

} // namespace urma_log_helper
} // namespace diag
