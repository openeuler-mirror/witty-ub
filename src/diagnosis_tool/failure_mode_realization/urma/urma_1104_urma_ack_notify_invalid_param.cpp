#include "urma_1104_urma_ack_notify_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1104UrmaAckNotifyInvalidParam> g_urma("urma_1104");

bool Urma1104UrmaAckNotifyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1104UrmaAckNotifyInvalidParam::GetName() const
{
    return "urma_ack_notify 参数非法";
}

std::string Urma1104UrmaAckNotifyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || notify == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma1104UrmaAckNotifyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1104UrmaAckNotifyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1104UrmaAckNotifyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1104UrmaAckNotifyInvalidParam::GetId() const
{
    return "urma_1104";
}
} // namespace diag
