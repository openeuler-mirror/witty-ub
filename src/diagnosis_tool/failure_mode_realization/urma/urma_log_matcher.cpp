#include "urma_log_matcher.h"

#include <cstdlib>
#include <filesystem>
#include <fstream>

namespace diag {
namespace {
bool MatchPattern(const std::string &line, const std::string &pattern)
{
    std::size_t linePos = 0;
    std::size_t patternPos = 0;
    bool sawWildcard = false;
    while (patternPos <= pattern.size()) {
        std::size_t wildcardPos = pattern.find('%', patternPos);
        std::string token = pattern.substr(patternPos, wildcardPos - patternPos);
        if (!token.empty()) {
            std::size_t found = line.find(token, linePos);
            if (found == std::string::npos) {
                return false;
            }
            linePos = found + token.size();
        }
        if (wildcardPos == std::string::npos) {
            return sawWildcard || token.empty() || linePos == line.size() || line.find(token) != std::string::npos;
        }
        sawWildcard = true;
        patternPos = wildcardPos + 1;
    }
    return true;
}

bool MatchFile(const std::filesystem::path &path, const std::vector<std::string> &patterns, std::string &logContent)
{
    std::ifstream input(path);
    if (!input.is_open()) {
        return false;
    }

    std::string line;
    while (std::getline(input, line)) {
        for (const auto &pattern : patterns) {
            if (MatchPattern(line, pattern)) {
                logContent = line;
                return true;
            }
        }
    }
    return false;
}
} // namespace

bool MatchUrmaLogLine(const std::vector<std::string> &patterns, std::string &logContent)
{
    logContent.clear();
    const char *logPath = std::getenv("URMA_LOG_PATH");
    if (logPath == nullptr || patterns.empty()) {
        return false;
    }

    std::error_code ec;
    std::filesystem::path path(logPath);
    if (std::filesystem::is_regular_file(path, ec)) {
        return MatchFile(path, patterns, logContent);
    }
    if (!std::filesystem::is_directory(path, ec)) {
        return false;
    }

    for (const auto &entry : std::filesystem::recursive_directory_iterator(
             path, std::filesystem::directory_options::skip_permission_denied, ec)) {
        if (ec) {
            break;
        }
        if (entry.is_regular_file(ec) && MatchFile(entry.path(), patterns, logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}
} // namespace diag
