#include "urma_0244_get_comp_urma_jetty_id_failed_get_comp_urma_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty> g_urma("urma_0244");

bool Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to get_comp_urma_jetty, Invalid type: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::GetName() const
{
    return "get_comp_urma_jetty_id Failed to get_comp_urma_jetty, Inval";
}

std::string Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常；该路径返回 NULL";
}

RootCause Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to get_comp_urma_jetty, Invalid type: %";
}

std::string Urma0244GetCompUrmaJettyIdFailedGetCompUrmaJetty::GetId() const
{
    return "urma_0244";
}
} // namespace diag
