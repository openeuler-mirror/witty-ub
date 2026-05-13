#include "urma_1089_urma_cmd_ack_async_event_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1089UrmaCmdAckAsyncEventInvalidParam> g_urma("urma_1089");

bool Urma1089UrmaCmdAckAsyncEventInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1089UrmaCmdAckAsyncEventInvalidParam::GetName() const
{
    return "urma_cmd_ack_async_event 参数非法";
}

std::string Urma1089UrmaCmdAckAsyncEventInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `event == NULL`";
}

RootCause Urma1089UrmaCmdAckAsyncEventInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1089UrmaCmdAckAsyncEventInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1089UrmaCmdAckAsyncEventInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1089UrmaCmdAckAsyncEventInvalidParam::GetId() const
{
    return "urma_1089";
}
} // namespace diag
