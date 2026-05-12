#include "urma_0591_urma_active_jfr_invalid_param_jfr_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0591UrmaActiveJfrInvalidParamJfrNull> g_urma("urma_0591");

bool Urma0591UrmaActiveJfrInvalidParamJfrNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0591UrmaActiveJfrInvalidParamJfrNull::GetName() const
{
    return "urma_active_jfr 参数非法（jfr == NULL）";
}

std::string Urma0591UrmaActiveJfrInvalidParamJfrNull::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0591UrmaActiveJfrInvalidParamJfrNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0591UrmaActiveJfrInvalidParamJfrNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0591UrmaActiveJfrInvalidParamJfrNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0591UrmaActiveJfrInvalidParamJfrNull::GetId() const
{
    return "urma_0591";
}
} // namespace diag
