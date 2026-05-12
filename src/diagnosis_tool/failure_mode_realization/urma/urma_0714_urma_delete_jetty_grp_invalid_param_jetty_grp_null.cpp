#include "urma_0714_urma_delete_jetty_grp_invalid_param_jetty_grp_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull> g_urma("urma_0714");

bool Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::GetName() const
{
    return "urma_delete_jetty_grp 参数非法（jetty_grp == NULL）";
}

std::string Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty_grp == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0714UrmaDeleteJettyGrpInvalidParamJettyGrpNull::GetId() const
{
    return "urma_0714";
}
} // namespace diag
