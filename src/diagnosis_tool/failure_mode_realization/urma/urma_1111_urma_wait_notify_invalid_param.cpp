#include "urma_1111_urma_wait_notify_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1111UrmaWaitNotifyInvalidParam> g_urma("urma_1111");

bool Urma1111UrmaWaitNotifyInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1111UrmaWaitNotifyInvalidParam::GetName() const
{
    return "urma_wait_notify 参数非法";
}

std::string Urma1111UrmaWaitNotifyInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `notifier == NULL || notifier->urma_ctx == NULL || notify == "
           "NULL`；该路径返回 -1";
}

RootCause Urma1111UrmaWaitNotifyInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1111UrmaWaitNotifyInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1111UrmaWaitNotifyInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1111UrmaWaitNotifyInvalidParam::GetId() const
{
    return "urma_1111";
}
} // namespace diag
