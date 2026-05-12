#include "urma_0600_urma_active_jfs_resource_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess> g_urma("urma_0600");

bool Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->active_jfs."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::GetName() const
{
    return "urma_active_jfs 激活资源失败（status != URMA_SUCCESS）";
}

std::string Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->active_jfs.";
}

std::string Urma0600UrmaActiveJfsResourceFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0600";
}
} // namespace diag
