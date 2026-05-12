#include "urma_1144_urma_cmd_unregister_seg_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1144UrmaCmdUnregisterSegIoctlCallFailure> g_urma("urma_1144");

bool Urma1144UrmaCmdUnregisterSegIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1144UrmaCmdUnregisterSegIoctlCallFailure::GetName() const
{
    return "urma_cmd_unregister_seg ioctl调用失败";
}

std::string Urma1144UrmaCmdUnregisterSegIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1144UrmaCmdUnregisterSegIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1144UrmaCmdUnregisterSegIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1144UrmaCmdUnregisterSegIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed, ret:%, errno:%.";
}

std::string Urma1144UrmaCmdUnregisterSegIoctlCallFailure::GetId() const
{
    return "urma_1144";
}
} // namespace diag
