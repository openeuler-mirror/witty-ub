#include "urma_0769_urma_free_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0769UrmaFreeJfsInvalidParam> g_urma("urma_0769");

bool Urma0769UrmaFreeJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0769UrmaFreeJfsInvalidParam::GetName() const
{
    return "urma_free_jfs 参数非法";
}

std::string Urma0769UrmaFreeJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0769UrmaFreeJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0769UrmaFreeJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0769UrmaFreeJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0769UrmaFreeJfsInvalidParam::GetId() const
{
    return "urma_0769";
}
} // namespace diag
