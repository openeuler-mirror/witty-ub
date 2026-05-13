#include "urma_0913_urma_set_context_opt_invalid_option_name.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0913UrmaSetContextOptInvalidOptionName> g_urma("urma_0913");

bool Urma0913UrmaSetContextOptInvalidOptionName::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid option name."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0913UrmaSetContextOptInvalidOptionName::GetName() const
{
    return "urma_set_context_opt Invalid option name.";
}

std::string Urma0913UrmaSetContextOptInvalidOptionName::GetRootCauseDesc() const
{
    return "函数参数校验失败；该路径返回 URMA_EINVAL";
}

RootCause Urma0913UrmaSetContextOptInvalidOptionName::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0913UrmaSetContextOptInvalidOptionName::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0913UrmaSetContextOptInvalidOptionName::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid option name.";
}

std::string Urma0913UrmaSetContextOptInvalidOptionName::GetId() const
{
    return "urma_0913";
}
} // namespace diag
