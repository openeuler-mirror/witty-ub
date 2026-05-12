#include "urma_0347_urma_cmd_active_jetty_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0347UrmaCmdActiveJettyIoctlCallFailure> g_urma("urma_0347");

bool Urma0347UrmaCmdActiveJettyIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_active_jetty, ret:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0347UrmaCmdActiveJettyIoctlCallFailure::GetName() const
{
    return "urma_cmd_active_jetty ioctl调用失败";
}

std::string Urma0347UrmaCmdActiveJettyIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0347UrmaCmdActiveJettyIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0347UrmaCmdActiveJettyIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0347UrmaCmdActiveJettyIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_active_jetty, ret:%.";
}

std::string Urma0347UrmaCmdActiveJettyIoctlCallFailure::GetId() const
{
    return "urma_0347";
}
} // namespace diag
