#include "urma_0696_urma_deactive_jfr_resource_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess> g_urma("urma_0696");

bool Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->deactive_jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::GetName() const
{
    return "urma_deactive_jfr 激活资源失败（status != URMA_SUCCESS）";
}

std::string Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->deactive_jfr.";
}

std::string Urma0696UrmaDeactiveJfrResourceFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0696";
}
} // namespace diag
