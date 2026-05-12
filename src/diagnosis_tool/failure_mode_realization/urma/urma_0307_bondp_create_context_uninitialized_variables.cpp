#include "urma_0307_bondp_create_context_uninitialized_variables.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0307BondpCreateContextUninitializedVariables> g_urma("urma_0307");

bool Urma0307BondpCreateContextUninitializedVariables::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Uninitialized variables"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0307BondpCreateContextUninitializedVariables::GetName() const
{
    return "bondp_create_context Uninitialized variables";
}

std::string Urma0307BondpCreateContextUninitializedVariables::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `!g_bondp_global_ctx`；该路径返回 NULL";
}

RootCause Urma0307BondpCreateContextUninitializedVariables::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0307BondpCreateContextUninitializedVariables::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0307BondpCreateContextUninitializedVariables::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Uninitialized variables";
}

std::string Urma0307BondpCreateContextUninitializedVariables::GetId() const
{
    return "urma_0307";
}
} // namespace diag
