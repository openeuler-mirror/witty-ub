#include "urma_0605_urma_advise_jetty_invalid_param_ops_null_ops_advise_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty> g_urma("urma_0605");

bool Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::GetName() const
{
    return "urma_advise_jetty 参数非法（ops == NULL || ops->advise_jetty == NULL）";
}

std::string Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ops == NULL || ops->advise_jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0605UrmaAdviseJettyInvalidParamOpsNullOpsAdviseJetty::GetId() const
{
    return "urma_0605";
}
} // namespace diag
