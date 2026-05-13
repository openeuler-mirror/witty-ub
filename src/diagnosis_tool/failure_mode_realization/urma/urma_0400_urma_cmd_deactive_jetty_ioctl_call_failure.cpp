#include "urma_0400_urma_cmd_deactive_jetty_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0400UrmaCmdDeactiveJettyIoctlCallFailure> g_urma("urma_0400");

bool Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_deactive_jetty, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::GetName() const
{
    return "urma_cmd_deactive_jetty ioctl调用失败";
}

std::string Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_deactive_jetty, ret:%, errno:%.";
}

std::string Urma0400UrmaCmdDeactiveJettyIoctlCallFailure::GetId() const
{
    return "urma_0400";
}
} // namespace diag
