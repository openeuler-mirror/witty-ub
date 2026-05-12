#include "urma_0819_urma_query_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0819UrmaQueryJfsInvalidParam> g_urma("urma_0819");

bool Urma0819UrmaQueryJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0819UrmaQueryJfsInvalidParam::GetName() const
{
    return "urma_query_jfs 参数非法";
}

std::string Urma0819UrmaQueryJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || cfg == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0819UrmaQueryJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0819UrmaQueryJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0819UrmaQueryJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0819UrmaQueryJfsInvalidParam::GetId() const
{
    return "urma_0819";
}
} // namespace diag
