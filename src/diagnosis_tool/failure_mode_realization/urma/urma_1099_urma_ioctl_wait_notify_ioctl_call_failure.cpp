#include "urma_1099_urma_ioctl_wait_notify_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1099UrmaIoctlWaitNotifyIoctlCallFailure> g_urma("urma_1099");

bool Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"wait notify ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::GetName() const
{
    return "urma_ioctl_wait_notify ioctl调用失败";
}

std::string Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：wait notify ioctl failed, ret:%, errno:%.";
}

std::string Urma1099UrmaIoctlWaitNotifyIoctlCallFailure::GetId() const
{
    return "urma_1099";
}
} // namespace diag
