#include "kvcache_log_helper.h"

#include <regex>
#include <sstream>

#include "../urma/urma_log_helper.h"

namespace diag {
namespace kvcache_log_helper {

std::string RunCommand(const std::string &cmd)
{
    return urma_log_helper::RunCommand(cmd);
}

bool ParseFailureLogLine(const std::string &line, FailureLogInfo &logInfo)
{
    return urma_log_helper::ParseFailureLogLine(line, logInfo);
}

// 当grep匹配多个文件时，输出格式为"文件路径:日志行"，
// 需要去掉文件路径前缀，只保留日志行内容
// Strip filepath prefix from multi-file grep output (e.g., "some.log:2026-05-13T..." -> "2026-05-13T...")
// 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
std::string StripFilepathPrefixFromOutput(const std::string &grepOutput)
{
    static const std::regex logTimestampPattern(R"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})");
    std::istringstream rawIss(grepOutput);
    std::string processedOutput, rawLine;
    while (std::getline(rawIss, rawLine)) {
        std::smatch match;
        if (std::regex_search(rawLine, match, logTimestampPattern)) {
            processedOutput += rawLine.substr(match.position()) + "\n";
        } else {
            processedOutput += rawLine + "\n";
        }
    }
    return processedOutput;
}

} // namespace kvcache_log_helper
} // namespace diag
