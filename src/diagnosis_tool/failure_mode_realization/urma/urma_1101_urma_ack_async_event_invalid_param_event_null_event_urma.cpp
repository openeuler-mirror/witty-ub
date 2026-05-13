#include "urma_1101_urma_ack_async_event_invalid_param_event_null_event_urma.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma> g_urma("urma_1101");

bool Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::GetName() const
{
    return "urma_ack_async_event 参数非法（event == NULL || event->urma_ctx == NULL）";
}

std::string Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `event == NULL || event->urma_ctx == NULL`";
}

RootCause Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1101UrmaAckAsyncEventInvalidParamEventNullEventUrma::GetId() const
{
    return "urma_1101";
}
} // namespace diag
