#include "urma_0692_urma_deactive_jfc_resource_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess> g_urma("urma_0692");

bool Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->deactive_jfc."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::GetName() const
{
    return "urma_deactive_jfc 激活资源失败（status != URMA_SUCCESS）";
}

std::string Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->deactive_jfc.";
}

std::string Urma0692UrmaDeactiveJfcResourceFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0692";
}
} // namespace diag
