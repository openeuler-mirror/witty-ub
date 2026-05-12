#include "urma_0589_urma_active_jfc_resource_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess> g_urma("urma_0589");

bool Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->active_jfc."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::GetName() const
{
    return "urma_active_jfc 激活资源失败（status != URMA_SUCCESS）";
}

std::string Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->active_jfc.";
}

std::string Urma0589UrmaActiveJfcResourceFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0589";
}
} // namespace diag
