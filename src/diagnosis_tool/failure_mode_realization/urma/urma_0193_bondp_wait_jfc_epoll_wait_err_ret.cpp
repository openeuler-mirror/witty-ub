#include "urma_0193_bondp_wait_jfc_epoll_wait_err_ret.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0193BondpWaitJfcEpollWaitErrRet> g_urma("urma_0193");

bool Urma0193BondpWaitJfcEpollWaitErrRet::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Epoll wait err, ret:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0193BondpWaitJfcEpollWaitErrRet::GetName() const
{
    return "bondp_wait_jfc Epoll wait err, ret:%.";
}

std::string Urma0193BondpWaitJfcEpollWaitErrRet::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `num < 0 || num > epoll_event_limit`；该路径返回 -1";
}

RootCause Urma0193BondpWaitJfcEpollWaitErrRet::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0193BondpWaitJfcEpollWaitErrRet::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0193BondpWaitJfcEpollWaitErrRet::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Epoll wait err, ret:%.";
}

std::string Urma0193BondpWaitJfcEpollWaitErrRet::GetId() const
{
    return "urma_0193";
}
} // namespace diag
