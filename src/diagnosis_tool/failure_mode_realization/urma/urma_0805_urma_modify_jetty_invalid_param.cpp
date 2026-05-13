#include "urma_0805_urma_modify_jetty_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0805UrmaModifyJettyInvalidParam> g_urma("urma_0805");

bool Urma0805UrmaModifyJettyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0805UrmaModifyJettyInvalidParam::GetName() const
{
    return "urma_modify_jetty 参数非法";
}

std::string Urma0805UrmaModifyJettyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jetty == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0805UrmaModifyJettyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0805UrmaModifyJettyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0805UrmaModifyJettyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0805UrmaModifyJettyInvalidParam::GetId() const
{
    return "urma_0805";
}
} // namespace diag
