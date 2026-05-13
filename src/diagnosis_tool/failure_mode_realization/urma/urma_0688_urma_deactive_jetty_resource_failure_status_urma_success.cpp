#include "urma_0688_urma_deactive_jetty_resource_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess> g_urma("urma_0688");

bool Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to exec ops->deactive_jetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::GetName() const
{
    return "urma_deactive_jetty 激活资源失败（status != URMA_SUCCESS）";
}

std::string Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "status";
}

RootCause Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to exec ops->deactive_jetty.";
}

std::string Urma0688UrmaDeactiveJettyResourceFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0688";
}
} // namespace diag
