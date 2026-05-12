#include "urma_0577_urma_ioctl_wait_jfc_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0577UrmaIoctlWaitJfcIoctlCallFailure> g_urma("urma_0577");

bool Urma0577UrmaIoctlWaitJfcIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"wait jfc ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0577UrmaIoctlWaitJfcIoctlCallFailure::GetName() const
{
    return "urma_ioctl_wait_jfc ioctl调用失败";
}

std::string Urma0577UrmaIoctlWaitJfcIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0577UrmaIoctlWaitJfcIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0577UrmaIoctlWaitJfcIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0577UrmaIoctlWaitJfcIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：wait jfc ioctl failed, ret:%, errno:%.";
}

std::string Urma0577UrmaIoctlWaitJfcIoctlCallFailure::GetId() const
{
    return "urma_0577";
}
} // namespace diag
