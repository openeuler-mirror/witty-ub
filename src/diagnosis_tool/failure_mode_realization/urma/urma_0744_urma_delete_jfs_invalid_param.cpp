#include "urma_0744_urma_delete_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0744UrmaDeleteJfsInvalidParam> g_urma("urma_0744");

bool Urma0744UrmaDeleteJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0744UrmaDeleteJfsInvalidParam::GetName() const
{
    return "urma_delete_jfs 参数非法";
}

std::string Urma0744UrmaDeleteJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0744UrmaDeleteJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0744UrmaDeleteJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0744UrmaDeleteJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0744UrmaDeleteJfsInvalidParam::GetId() const
{
    return "urma_0744";
}
} // namespace diag
