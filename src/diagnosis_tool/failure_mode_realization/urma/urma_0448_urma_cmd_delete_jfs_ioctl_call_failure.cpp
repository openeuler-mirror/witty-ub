#include "urma_0448_urma_cmd_delete_jfs_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0448UrmaCmdDeleteJfsIoctlCallFailure> g_urma("urma_0448");

bool Urma0448UrmaCmdDeleteJfsIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0448UrmaCmdDeleteJfsIoctlCallFailure::GetName() const
{
    return "urma_cmd_delete_jfs ioctl调用失败";
}

std::string Urma0448UrmaCmdDeleteJfsIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0448UrmaCmdDeleteJfsIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0448UrmaCmdDeleteJfsIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0448UrmaCmdDeleteJfsIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed, ret:%, errno:%.";
}

std::string Urma0448UrmaCmdDeleteJfsIoctlCallFailure::GetId() const
{
    return "urma_0448";
}
} // namespace diag
