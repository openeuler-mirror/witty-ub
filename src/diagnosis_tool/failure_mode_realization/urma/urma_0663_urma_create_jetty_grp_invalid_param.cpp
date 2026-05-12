#include "urma_0663_urma_create_jetty_grp_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0663UrmaCreateJettyGrpInvalidParam> g_urma("urma_0663");

bool Urma0663UrmaCreateJettyGrpInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0663UrmaCreateJettyGrpInvalidParam::GetName() const
{
    return "urma_create_jetty_grp 参数非法";
}

std::string Urma0663UrmaCreateJettyGrpInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || cfg == NULL || strnlen(cfg->name, URMA_MAX_NAME) >= "
           "URMA_MAX_NAME`；该路径返回 NULL";
}

RootCause Urma0663UrmaCreateJettyGrpInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0663UrmaCreateJettyGrpInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0663UrmaCreateJettyGrpInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0663UrmaCreateJettyGrpInvalidParam::GetId() const
{
    return "urma_0663";
}
} // namespace diag
