#include "urma_0583_urma_active_jetty_resource_failure_jetty_urma_jetty_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs> g_urma("urma_0583");

bool Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Jetty state is wrong in active_jetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::GetName() const
{
    return "urma_active_jetty 激活资源失败（jetty->urma_jetty_opt.is_actived == true）";
}

std::string Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Jetty state is wrong in active_jetty.";
}

std::string Urma0583UrmaActiveJettyResourceFailureJettyUrmaJettyOptIs::GetId() const
{
    return "urma_0583";
}
} // namespace diag
