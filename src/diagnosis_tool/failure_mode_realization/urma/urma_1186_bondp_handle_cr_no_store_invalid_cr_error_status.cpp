#include "urma_1186_bondp_handle_cr_no_store_invalid_cr_error_status.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus> g_urma("urma_1186");

bool Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid cr error status: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::GetName() const
{
    return "bondp_handle_cr_no_store Invalid cr error status: %";
}

std::string Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 "
           "CONVERT_FAIL";
}

RootCause Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid cr error status: %";
}

std::string Urma1186BondpHandleCrNoStoreInvalidCrErrorStatus::GetId() const
{
    return "urma_1186";
}
} // namespace diag
