#include "urma_0595_urma_active_jfr_resource_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess> g_urma("urma_0595");

bool Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->active_jfr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::GetName() const
{
    return "urma_active_jfr 激活资源失败（status != URMA_SUCCESS）";
}

std::string Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->active_jfr.";
}

std::string Urma0595UrmaActiveJfrResourceFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0595";
}
} // namespace diag
