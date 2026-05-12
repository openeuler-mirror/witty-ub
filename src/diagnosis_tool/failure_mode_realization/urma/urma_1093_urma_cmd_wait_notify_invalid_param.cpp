#include "urma_1093_urma_cmd_wait_notify_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1093UrmaCmdWaitNotifyInvalidParam> g_urma("urma_1093");

bool Urma1093UrmaCmdWaitNotifyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1093UrmaCmdWaitNotifyInvalidParam::GetName() const
{
    return "urma_cmd_wait_notify 参数非法";
}

std::string Urma1093UrmaCmdWaitNotifyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `notifier == NULL || notifier->fd < 0 || notify == NULL`；该路径返回 -1";
}

RootCause Urma1093UrmaCmdWaitNotifyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1093UrmaCmdWaitNotifyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1093UrmaCmdWaitNotifyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1093UrmaCmdWaitNotifyInvalidParam::GetId() const
{
    return "urma_1093";
}
} // namespace diag
