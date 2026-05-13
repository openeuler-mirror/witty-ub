#include "urma_0946_urma_cmd_get_smac_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0946UrmaCmdGetSmacInvalidParam> g_urma("urma_0946");

bool Urma0946UrmaCmdGetSmacInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0946UrmaCmdGetSmacInvalidParam::GetName() const
{
    return "urma_cmd_get_smac 参数非法";
}

std::string Urma0946UrmaCmdGetSmacInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || mac == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0946UrmaCmdGetSmacInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0946UrmaCmdGetSmacInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0946UrmaCmdGetSmacInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0946UrmaCmdGetSmacInvalidParam::GetId() const
{
    return "urma_0946";
}
} // namespace diag
