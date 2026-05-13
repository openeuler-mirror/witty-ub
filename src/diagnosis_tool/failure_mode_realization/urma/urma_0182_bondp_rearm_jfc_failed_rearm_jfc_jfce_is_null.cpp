#include "urma_0182_bondp_rearm_jfc_failed_rearm_jfc_jfce_is_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull> g_urma("urma_0182");

bool Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to rearm jfc: JFCE is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::GetName() const
{
    return "bondp_rearm_jfc Failed to rearm jfc: JFCE is NULL";
}

std::string Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `bdp_jfc->v_jfc.jfc_cfg.jfce == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to rearm jfc: JFCE is NULL";
}

std::string Urma0182BondpRearmJfcFailedRearmJfcJfceIsNull::GetId() const
{
    return "urma_0182";
}
} // namespace diag
