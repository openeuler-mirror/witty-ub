#include "urma_0615_urma_alloc_jetty_invalid_param_urma_create_jetty_check_trans.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans> g_urma("urma_0615");

bool Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::GetName() const
{
    return "urma_alloc_jetty 参数非法（urma_create_jetty_check_trans_mode(urma_ctx, cfg) != 0）";
}

std::string Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_create_jetty_check_trans_mode(urma_ctx, cfg) != 0`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0615UrmaAllocJettyInvalidParamUrmaCreateJettyCheckTrans::GetId() const
{
    return "urma_0615";
}
} // namespace diag
