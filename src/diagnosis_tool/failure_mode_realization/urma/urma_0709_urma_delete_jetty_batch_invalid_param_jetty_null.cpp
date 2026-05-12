#include "urma_0709_urma_delete_jetty_batch_invalid_param_jetty_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull> g_urma("urma_0709");

bool Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index % jetty in the array is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::GetName() const
{
    return "urma_delete_jetty_batch 参数非法（jetty == NULL）";
}

std::string Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL`";
}

RootCause Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index % jetty in the array is NULL.";
}

std::string Urma0709UrmaDeleteJettyBatchInvalidParamJettyNull::GetId() const
{
    return "urma_0709";
}
} // namespace diag
