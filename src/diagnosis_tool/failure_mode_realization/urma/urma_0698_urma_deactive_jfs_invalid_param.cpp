#include "urma_0698_urma_deactive_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0698UrmaDeactiveJfsInvalidParam> g_urma("urma_0698");

bool Urma0698UrmaDeactiveJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0698UrmaDeactiveJfsInvalidParam::GetName() const
{
    return "urma_deactive_jfs 参数非法";
}

std::string Urma0698UrmaDeactiveJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0698UrmaDeactiveJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0698UrmaDeactiveJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0698UrmaDeactiveJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0698UrmaDeactiveJfsInvalidParam::GetId() const
{
    return "urma_0698";
}
} // namespace diag
