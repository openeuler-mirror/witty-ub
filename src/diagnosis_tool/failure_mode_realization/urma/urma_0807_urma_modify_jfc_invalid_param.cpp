#include "urma_0807_urma_modify_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0807UrmaModifyJfcInvalidParam> g_urma("urma_0807");

bool Urma0807UrmaModifyJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0807UrmaModifyJfcInvalidParam::GetName() const
{
    return "urma_modify_jfc 参数非法";
}

std::string Urma0807UrmaModifyJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL || attr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0807UrmaModifyJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0807UrmaModifyJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0807UrmaModifyJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0807UrmaModifyJfcInvalidParam::GetId() const
{
    return "urma_0807";
}
} // namespace diag
