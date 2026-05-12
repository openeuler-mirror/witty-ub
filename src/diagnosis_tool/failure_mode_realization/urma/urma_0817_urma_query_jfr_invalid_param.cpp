#include "urma_0817_urma_query_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0817UrmaQueryJfrInvalidParam> g_urma("urma_0817");

bool Urma0817UrmaQueryJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0817UrmaQueryJfrInvalidParam::GetName() const
{
    return "urma_query_jfr 参数非法";
}

std::string Urma0817UrmaQueryJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL || cfg == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0817UrmaQueryJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0817UrmaQueryJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0817UrmaQueryJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0817UrmaQueryJfrInvalidParam::GetId() const
{
    return "urma_0817";
}
} // namespace diag
