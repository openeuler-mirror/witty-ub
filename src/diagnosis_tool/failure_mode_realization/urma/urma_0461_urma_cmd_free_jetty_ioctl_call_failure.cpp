#include "urma_0461_urma_cmd_free_jetty_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0461UrmaCmdFreeJettyIoctlCallFailure> g_urma("urma_0461");

bool Urma0461UrmaCmdFreeJettyIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0461UrmaCmdFreeJettyIoctlCallFailure::GetName() const
{
    return "urma_cmd_free_jetty ioctl调用失败";
}

std::string Urma0461UrmaCmdFreeJettyIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求";
}

RootCause Urma0461UrmaCmdFreeJettyIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0461UrmaCmdFreeJettyIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0461UrmaCmdFreeJettyIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed, ret:%, errno:%.";
}

std::string Urma0461UrmaCmdFreeJettyIoctlCallFailure::GetId() const
{
    return "urma_0461";
}
} // namespace diag
