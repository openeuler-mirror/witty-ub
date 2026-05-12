#include "urma_0356_urma_cmd_active_jfs_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0356UrmaCmdActiveJfsIoctlCallFailure> g_urma("urma_0356");

bool Urma0356UrmaCmdActiveJfsIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_active_jfs, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0356UrmaCmdActiveJfsIoctlCallFailure::GetName() const
{
    return "urma_cmd_active_jfs ioctl调用失败";
}

std::string Urma0356UrmaCmdActiveJfsIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0356UrmaCmdActiveJfsIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0356UrmaCmdActiveJfsIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0356UrmaCmdActiveJfsIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_active_jfs, ret:%, errno:%.";
}

std::string Urma0356UrmaCmdActiveJfsIoctlCallFailure::GetId() const
{
    return "urma_0356";
}
} // namespace diag
