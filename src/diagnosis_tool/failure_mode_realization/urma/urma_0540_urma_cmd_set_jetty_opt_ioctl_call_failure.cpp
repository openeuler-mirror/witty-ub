#include "urma_0540_urma_cmd_set_jetty_opt_ioctl_call_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0540UrmaCmdSetJettyOptIoctlCallFailure> g_urma("urma_0540");

bool Urma0540UrmaCmdSetJettyOptIoctlCallFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"ioctl failed in urma_cmd_set_jetty_opt, ret:%, errno:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0540UrmaCmdSetJettyOptIoctlCallFailure::GetName() const
{
    return "urma_cmd_set_jetty_opt ioctl调用失败";
}

std::string Urma0540UrmaCmdSetJettyOptIoctlCallFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0540UrmaCmdSetJettyOptIoctlCallFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0540UrmaCmdSetJettyOptIoctlCallFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0540UrmaCmdSetJettyOptIoctlCallFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：ioctl failed in urma_cmd_set_jetty_opt, ret:%, errno:%.";
}

std::string Urma0540UrmaCmdSetJettyOptIoctlCallFailure::GetId() const
{
    return "urma_0540";
}
} // namespace diag
