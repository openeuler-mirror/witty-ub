#include "urma_0581_urma_active_jetty_invalid_param_urma_create_jetty_check_trans.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans> g_urma("urma_0581");

bool Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::GetName() const
{
    return "urma_active_jetty 参数非法（urma_create_jetty_check_trans_mode(urma_ctx, cfg) != 0）";
}

std::string Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_create_jetty_check_trans_mode(urma_ctx, cfg) != 0`；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0581UrmaActiveJettyInvalidParamUrmaCreateJettyCheckTrans::GetId() const
{
    return "urma_0581";
}
} // namespace diag
