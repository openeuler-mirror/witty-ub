#include "urma_1169_urma_cmd_create_notifier_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1169UrmaCmdCreateNotifierIoctlCallFailure> g_urma("urma_1169");

bool Urma1169UrmaCmdCreateNotifierIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_create_notifier, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1169UrmaCmdCreateNotifierIoctlCallFailure::GetName() const
{
    return "urma_cmd_create_notifier ioctl调用失败";
}

std::string Urma1169UrmaCmdCreateNotifierIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 -1";
}

RootCause Urma1169UrmaCmdCreateNotifierIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1169UrmaCmdCreateNotifierIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1169UrmaCmdCreateNotifierIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_create_notifier, ret:%, errno:%.";
}

std::string Urma1169UrmaCmdCreateNotifierIoctlCallFailure::GetId() const
{
    return "urma_1169";
}
} // namespace diag
