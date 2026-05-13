#include "urma_1051_bondp_delete_comp_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1051BondpDeleteCompInvalidParam> g_urma("urma_1051");

bool Urma1051BondpDeleteCompInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1051BondpDeleteCompInvalidParam::GetName() const
{
    return "bondp_delete_comp Invalid param";
}

std::string Urma1051BondpDeleteCompInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(comp)`；该路径返回 URMA_EINVAL";
}

RootCause Urma1051BondpDeleteCompInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1051BondpDeleteCompInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1051BondpDeleteCompInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param";
}

std::string Urma1051BondpDeleteCompInvalidParam::GetId() const
{
    return "urma_1051";
}
} // namespace diag
