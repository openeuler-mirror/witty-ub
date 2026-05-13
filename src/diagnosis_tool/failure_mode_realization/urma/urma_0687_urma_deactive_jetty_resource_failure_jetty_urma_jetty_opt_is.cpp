#include "urma_0687_urma_deactive_jetty_resource_failure_jetty_urma_jetty_opt_is.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs> g_urma("urma_0687");

bool Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Jetty state is wrong in deactive_jetty."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::GetName() const
{
    return "urma_deactive_jetty 激活资源失败（jetty->urma_jetty_opt.is_actived == false）";
}

std::string Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Jetty state is wrong in deactive_jetty.";
}

std::string Urma0687UrmaDeactiveJettyResourceFailureJettyUrmaJettyOptIs::GetId() const
{
    return "urma_0687";
}
} // namespace diag
