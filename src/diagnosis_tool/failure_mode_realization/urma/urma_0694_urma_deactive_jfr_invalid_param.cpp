#include "urma_0694_urma_deactive_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0694UrmaDeactiveJfrInvalidParam> g_urma("urma_0694");

bool Urma0694UrmaDeactiveJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0694UrmaDeactiveJfrInvalidParam::GetName() const
{
    return "urma_deactive_jfr 参数非法";
}

std::string Urma0694UrmaDeactiveJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0694UrmaDeactiveJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0694UrmaDeactiveJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0694UrmaDeactiveJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0694UrmaDeactiveJfrInvalidParam::GetId() const
{
    return "urma_0694";
}
} // namespace diag
