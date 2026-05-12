#include "urma_0414_urma_cmd_delete_jetty_batch_invalid_param_jetty_arr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull> g_urma("urma_0414");

bool Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::GetName() const
{
    return "urma_cmd_delete_jetty_batch 参数非法（jetty_arr == NULL || jetty_num <= 0 || bad_jetty == NULL）";
}

std::string Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty_arr == NULL || jetty_num <= 0 || bad_jetty == NULL`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma0414UrmaCmdDeleteJettyBatchInvalidParamJettyArrNull::GetId() const
{
    return "urma_0414";
}
} // namespace diag
