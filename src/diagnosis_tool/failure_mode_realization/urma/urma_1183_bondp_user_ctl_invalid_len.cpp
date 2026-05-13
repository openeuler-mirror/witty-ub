#include "urma_1183_bondp_user_ctl_invalid_len.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1183BondpUserCtlInvalidLen> g_urma("urma_1183");

bool Urma1183BondpUserCtlInvalidLen::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid len"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1183BondpUserCtlInvalidLen::GetName() const
{
    return "bondp_user_ctl Invalid len";
}

std::string Urma1183BondpUserCtlInvalidLen::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `in->len != sizeof(urma_context_aggr_mode_t)`；该路径返回 -EINVAL";
}

RootCause Urma1183BondpUserCtlInvalidLen::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1183BondpUserCtlInvalidLen::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1183BondpUserCtlInvalidLen::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid len";
}

std::string Urma1183BondpUserCtlInvalidLen::GetId() const
{
    return "urma_1183";
}
} // namespace diag
