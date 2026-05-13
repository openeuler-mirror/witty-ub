#include "urma_1216_urma_check_opt_valid_invalid_opt_len.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1216UrmaCheckOptValidInvalidOptLen> g_urma("urma_1216");

bool Urma1216UrmaCheckOptValidInvalidOptLen::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"invalid opt len"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1216UrmaCheckOptValidInvalidOptLen::GetName() const
{
    return "urma_check_opt_valid invalid opt len";
}

std::string Urma1216UrmaCheckOptValidInvalidOptLen::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `table[i].size != len`；该路径返回 URMA_EINVAL";
}

RootCause Urma1216UrmaCheckOptValidInvalidOptLen::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1216UrmaCheckOptValidInvalidOptLen::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1216UrmaCheckOptValidInvalidOptLen::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：invalid opt len";
}

std::string Urma1216UrmaCheckOptValidInvalidOptLen::GetId() const
{
    return "urma_1216";
}
} // namespace diag
