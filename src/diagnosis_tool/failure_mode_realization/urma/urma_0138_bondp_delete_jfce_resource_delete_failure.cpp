#include "urma_0138_bondp_delete_jfce_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0138BondpDeleteJfceResourceDeleteFailure> g_urma("urma_0138");

bool Urma0138BondpDeleteJfceResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete jfce[%], still in use. use_cnt: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0138BondpDeleteJfceResourceDeleteFailure::GetName() const
{
    return "bondp_delete_jfce 删除资源失败";
}

std::string Urma0138BondpDeleteJfceResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EAGAIN";
}

RootCause Urma0138BondpDeleteJfceResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0138BondpDeleteJfceResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0138BondpDeleteJfceResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete jfce[%], still in use. use_cnt: %";
}

std::string Urma0138BondpDeleteJfceResourceDeleteFailure::GetId() const
{
    return "urma_0138";
}
} // namespace diag
