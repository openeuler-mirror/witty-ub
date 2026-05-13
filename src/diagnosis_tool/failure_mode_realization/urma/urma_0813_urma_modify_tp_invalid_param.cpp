#include "urma_0813_urma_modify_tp_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0813UrmaModifyTpInvalidParam> g_urma("urma_0813");

bool Urma0813UrmaModifyTpInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0813UrmaModifyTpInvalidParam::GetName() const
{
    return "urma_modify_tp 参数非法";
}

std::string Urma0813UrmaModifyTpInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || cfg == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0813UrmaModifyTpInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0813UrmaModifyTpInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0813UrmaModifyTpInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0813UrmaModifyTpInvalidParam::GetId() const
{
    return "urma_0813";
}
} // namespace diag
