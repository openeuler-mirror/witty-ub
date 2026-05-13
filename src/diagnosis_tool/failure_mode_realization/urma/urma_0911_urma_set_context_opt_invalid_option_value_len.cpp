#include "urma_0911_urma_set_context_opt_invalid_option_value_len.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0911UrmaSetContextOptInvalidOptionValueLen> g_urma("urma_0911");

bool Urma0911UrmaSetContextOptInvalidOptionValueLen::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid option value len."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0911UrmaSetContextOptInvalidOptionValueLen::GetName() const
{
    return "urma_set_context_opt Invalid option value len.";
}

std::string Urma0911UrmaSetContextOptInvalidOptionValueLen::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `opt_len != sizeof(urma_context_aggr_mode_t)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0911UrmaSetContextOptInvalidOptionValueLen::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0911UrmaSetContextOptInvalidOptionValueLen::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0911UrmaSetContextOptInvalidOptionValueLen::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid option value len.";
}

std::string Urma0911UrmaSetContextOptInvalidOptionValueLen::GetId() const
{
    return "urma_0911";
}
} // namespace diag
