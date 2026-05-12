#include "urma_1053_bondp_delete_comp_default_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1053BondpDeleteCompDefaultResourceDeleteFailure> g_urma("urma_1053");

bool Urma1053BondpDeleteCompDefaultResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete comp % type %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1053BondpDeleteCompDefaultResourceDeleteFailure::GetName() const
{
    return "bondp_delete_comp_default 删除资源失败";
}

std::string Urma1053BondpDeleteCompDefaultResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma1053BondpDeleteCompDefaultResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1053BondpDeleteCompDefaultResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1053BondpDeleteCompDefaultResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete comp % type %";
}

std::string Urma1053BondpDeleteCompDefaultResourceDeleteFailure::GetId() const
{
    return "urma_1053";
}
} // namespace diag
