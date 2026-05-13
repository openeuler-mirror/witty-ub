#include "urma_1166_urma_cmd_create_context_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1166UrmaCmdCreateContextIoctlCallFailure> g_urma("urma_1166");

bool Urma1166UrmaCmdCreateContextIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1166UrmaCmdCreateContextIoctlCallFailure::GetName() const
{
    return "urma_cmd_create_context ioctl调用失败";
}

std::string Urma1166UrmaCmdCreateContextIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma1166UrmaCmdCreateContextIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1166UrmaCmdCreateContextIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1166UrmaCmdCreateContextIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed, ret:%, errno:%.";
}

std::string Urma1166UrmaCmdCreateContextIoctlCallFailure::GetId() const
{
    return "urma_1166";
}
} // namespace diag
