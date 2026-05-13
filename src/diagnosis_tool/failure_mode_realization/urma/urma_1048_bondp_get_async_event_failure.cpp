#include "urma_1048_bondp_get_async_event_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1048BondpGetAsyncEventFailure> g_urma("urma_1048");

bool Urma1048BondpGetAsyncEventFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"epoll_wait no event or err."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1048BondpGetAsyncEventFailure::GetName() const
{
    return "bondp_get_async_event 事件处理失败";
}

std::string Urma1048BondpGetAsyncEventFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `nfds == -1`；该路径返回 URMA_EVENT_ELR_ERR";
}

RootCause Urma1048BondpGetAsyncEventFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1048BondpGetAsyncEventFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1048BondpGetAsyncEventFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：epoll_wait no event or err.";
}

std::string Urma1048BondpGetAsyncEventFailure::GetId() const
{
    return "urma_1048";
}
} // namespace diag
