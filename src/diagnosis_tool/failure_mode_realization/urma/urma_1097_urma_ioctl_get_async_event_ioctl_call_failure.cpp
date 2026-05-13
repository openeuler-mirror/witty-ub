#include "urma_1097_urma_ioctl_get_async_event_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure> g_urma("urma_1097");

bool Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"get async event ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::GetName() const
{
    return "urma_ioctl_get_async_event ioctl调用失败";
}

std::string Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：get async event ioctl failed, ret:%, errno:%.";
}

std::string Urma1097UrmaIoctlGetAsyncEventIoctlCallFailure::GetId() const
{
    return "urma_1097";
}
} // namespace diag
