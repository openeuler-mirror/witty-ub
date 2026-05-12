#include "urma_0847_urma_unadvise_jetty_invalid_param_ops_null_ops_unadvise_jetty.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty> g_urma("urma_0847");

bool Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::GetName() const
{
    return "urma_unadvise_jetty 参数非法（ops == NULL || ops->unadvise_jetty == NULL）";
}

std::string Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ops == NULL || ops->unadvise_jetty == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0847UrmaUnadviseJettyInvalidParamOpsNullOpsUnadviseJetty::GetId() const
{
    return "urma_0847";
}
} // namespace diag
