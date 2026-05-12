#include "urma_1095_wait_async_event_ack_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1095WaitAsyncEventAckFailure> g_urma("urma_1095");

bool Urma1095WaitAsyncEventAckFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"There is an event and it must be acked, acked:%, reported:%"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1095WaitAsyncEventAckFailure::GetName() const
{
    return "wait_async_event_ack 确认事件失败";
}

std::string Urma1095WaitAsyncEventAckFailure::GetRootCauseDesc() const
{
    return "源码在该错误分支记录 URMA_LOG_ERR，通常表示当前函数检测到参数、状态、资源或下游返回值异常";
}

RootCause Urma1095WaitAsyncEventAckFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1095WaitAsyncEventAckFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1095WaitAsyncEventAckFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：There is an event and it must be acked, acked:%, reported:%";
}

std::string Urma1095WaitAsyncEventAckFailure::GetId() const
{
    return "urma_1095";
}
} // namespace diag
