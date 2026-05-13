#include "urma_0191_bondp_wait_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0191BondpWaitJfcInvalidParam> g_urma("urma_0191");

bool Urma0191BondpWaitJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid param"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0191BondpWaitJfcInvalidParam::GetName() const
{
    return "bondp_wait_jfc Invalid param";
}

std::string Urma0191BondpWaitJfcInvalidParam::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!is_valid_bondp_comp(bdp_jfce)`；该路径返回 URMA_EINVAL";
}

RootCause Urma0191BondpWaitJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0191BondpWaitJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0191BondpWaitJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid param";
}

std::string Urma0191BondpWaitJfcInvalidParam::GetId() const
{
    return "urma_0191";
}
} // namespace diag
