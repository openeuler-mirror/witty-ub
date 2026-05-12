#include "urma_0209_bondp_create_comp_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0209BondpCreateCompQueryAttrFailure> g_urma("urma_0209");

bool Urma0209BondpCreateCompQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get args list, type: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0209BondpCreateCompQueryAttrFailure::GetName() const
{
    return "bondp_create_comp 查询属性失败";
}

std::string Urma0209BondpCreateCompQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `args == NULL`";
}

RootCause Urma0209BondpCreateCompQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0209BondpCreateCompQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0209BondpCreateCompQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get args list, type: %.";
}

std::string Urma0209BondpCreateCompQueryAttrFailure::GetId() const
{
    return "urma_0209";
}
} // namespace diag
