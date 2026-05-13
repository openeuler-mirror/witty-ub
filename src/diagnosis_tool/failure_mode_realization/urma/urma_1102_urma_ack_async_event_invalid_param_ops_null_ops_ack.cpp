#include "urma_1102_urma_ack_async_event_invalid_param_ops_null_ops_ack.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck> g_urma("urma_1102");

bool Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter with ops nullptr."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::GetName() const
{
    return "urma_ack_async_event 参数非法（ops == NULL || ops->ack_async_event == NULL）";
}

std::string Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ops == NULL || ops->ack_async_event == NULL`";
}

RootCause Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter with ops nullptr.";
}

std::string Urma1102UrmaAckAsyncEventInvalidParamOpsNullOpsAck::GetId() const
{
    return "urma_1102";
}
} // namespace diag
