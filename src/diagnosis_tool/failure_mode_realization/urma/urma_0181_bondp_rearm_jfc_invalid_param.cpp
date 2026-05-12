#include "urma_0181_bondp_rearm_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0181BondpRearmJfcInvalidParam> g_urma("urma_0181");

bool Urma0181BondpRearmJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0181BondpRearmJfcInvalidParam::GetName() const
{
    return "bondp_rearm_jfc Invalid param";
}

std::string Urma0181BondpRearmJfcInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jfc)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0181BondpRearmJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0181BondpRearmJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0181BondpRearmJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param";
}

std::string Urma0181BondpRearmJfcInvalidParam::GetId() const
{
    return "urma_0181";
}
} // namespace diag
