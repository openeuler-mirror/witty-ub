#pragma once

#include <string>

#include "../../failure_log_info.h"

namespace diag {
namespace kvcache_log_helper {

std::string RunCommand(const std::string &cmd);
bool ParseFailureLogLine(const std::string &line, FailureLogInfo &logInfo);

// 当grep匹配多个文件时，输出格式为"文件路径:日志行"，
// 需要去掉文件路径前缀，只保留日志行内容
// Strip filepath prefix from multi-file grep output (e.g., "some.log:2026-05-13T..." -> "2026-05-13T...")
// 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
std::string StripFilepathPrefixFromOutput(const std::string &grepOutput);

} // namespace kvcache_log_helper
} // namespace diag
