#include "urma_0811_urma_modify_jfs_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0811UrmaModifyJfsInvalidParam> g_urma("urma_0811");

bool Urma0811UrmaModifyJfsInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0811UrmaModifyJfsInvalidParam::GetName() const
{
    return "urma_modify_jfs 参数非法";
}

std::string Urma0811UrmaModifyJfsInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0811UrmaModifyJfsInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0811UrmaModifyJfsInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0811UrmaModifyJfsInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0811UrmaModifyJfsInvalidParam::GetId() const
{
    return "urma_0811";
}
} // namespace diag
