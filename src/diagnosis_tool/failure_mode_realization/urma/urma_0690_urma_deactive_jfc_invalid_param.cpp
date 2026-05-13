#include "urma_0690_urma_deactive_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0690UrmaDeactiveJfcInvalidParam> g_urma("urma_0690");

bool Urma0690UrmaDeactiveJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0690UrmaDeactiveJfcInvalidParam::GetName() const
{
    return "urma_deactive_jfc 参数非法";
}

std::string Urma0690UrmaDeactiveJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfc == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0690UrmaDeactiveJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0690UrmaDeactiveJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0690UrmaDeactiveJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0690UrmaDeactiveJfcInvalidParam::GetId() const
{
    return "urma_0690";
}
} // namespace diag
