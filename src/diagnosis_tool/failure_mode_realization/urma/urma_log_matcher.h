#pragma once

#include <string>
#include <vector>

namespace diag {
bool MatchUrmaLogLine(const std::vector<std::string> &patterns, std::string &logContent);
} // namespace diag
