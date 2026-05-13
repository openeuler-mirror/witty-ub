#include "urma_0212_bondp_delete_comp_jfce_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0212BondpDeleteCompJfceResourceDeleteFailure> g_urma("urma_0212");

bool Urma0212BondpDeleteCompJfceResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete p_jfce, ret = %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0212BondpDeleteCompJfceResourceDeleteFailure::GetName() const
{
    return "bondp_delete_comp_jfce 删除资源失败";
}

std::string Urma0212BondpDeleteCompJfceResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_SUCCESS";
}

RootCause Urma0212BondpDeleteCompJfceResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0212BondpDeleteCompJfceResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0212BondpDeleteCompJfceResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete p_jfce, ret = %.";
}

std::string Urma0212BondpDeleteCompJfceResourceDeleteFailure::GetId() const
{
    return "urma_0212";
}
} // namespace diag
