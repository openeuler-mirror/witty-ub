#include "urma_1045_bondp_ack_async_event_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1045BondpAckAsyncEventInvalidParam> g_urma("urma_1045");

bool Urma1045BondpAckAsyncEventInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1045BondpAckAsyncEventInvalidParam::GetName() const
{
    return "bondp_ack_async_event 参数非法";
}

std::string Urma1045BondpAckAsyncEventInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `event->priv == NULL`";
}

RootCause Urma1045BondpAckAsyncEventInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1045BondpAckAsyncEventInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1045BondpAckAsyncEventInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1045BondpAckAsyncEventInvalidParam::GetId() const
{
    return "urma_1045";
}
} // namespace diag
