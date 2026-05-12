#include "urma_0580_urma_active_jetty_invalid_param_urma_create_jetty_check_jfc.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc> g_urma("urma_0580");

bool Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::GetName() const
{
    return "urma_active_jetty 参数非法（urma_create_jetty_check_jfc(cfg) != 0）";
}

std::string Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `urma_create_jetty_check_jfc(cfg) != 0`；该路径返回 URMA_EINVAL";
}

RootCause Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0580UrmaActiveJettyInvalidParamUrmaCreateJettyCheckJfc::GetId() const
{
    return "urma_0580";
}
} // namespace diag
