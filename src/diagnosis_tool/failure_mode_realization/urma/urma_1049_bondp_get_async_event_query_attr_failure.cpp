#include "urma_1049_bondp_get_async_event_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1049BondpGetAsyncEventQueryAttrFailure> g_urma("urma_1049");

bool Urma1049BondpGetAsyncEventQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"bondp get error epoll_event: 0x%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1049BondpGetAsyncEventQueryAttrFailure::GetName() const
{
    return "bondp_get_async_event 查询属性失败";
}

std::string Urma1049BondpGetAsyncEventQueryAttrFailure::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `(event.events & (EPOLLERR | EPOLLHUP | EPOLLRDHUP)) != 0`；该路径返回 "
           "URMA_EVENT_ELR_ERR";
}

RootCause Urma1049BondpGetAsyncEventQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1049BondpGetAsyncEventQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1049BondpGetAsyncEventQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：bondp get error epoll_event: 0x%.";
}

std::string Urma1049BondpGetAsyncEventQueryAttrFailure::GetId() const
{
    return "urma_1049";
}
} // namespace diag
