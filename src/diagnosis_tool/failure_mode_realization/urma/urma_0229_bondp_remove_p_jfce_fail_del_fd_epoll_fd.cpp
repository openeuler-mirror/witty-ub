#include "urma_0229_bondp_remove_p_jfce_fail_del_fd_epoll_fd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0229BondpRemovePJfceFailDelFdEpollFd> g_urma("urma_0229");

bool Urma0229BondpRemovePJfceFailDelFdEpollFd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Fail to del fd:% to epoll fd:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0229BondpRemovePJfceFailDelFdEpollFd::GetName() const
{
    return "bondp_remove_p_jfce Fail to del fd:% to epoll fd:%.";
}

std::string Urma0229BondpRemovePJfceFailDelFdEpollFd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `epoll_ctl(v_jfce->fd, EPOLL_CTL_DEL, p_jfce->fd, &ev) != 0`";
}

RootCause Urma0229BondpRemovePJfceFailDelFdEpollFd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0229BondpRemovePJfceFailDelFdEpollFd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0229BondpRemovePJfceFailDelFdEpollFd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Fail to del fd:% to epoll fd:%.";
}

std::string Urma0229BondpRemovePJfceFailDelFdEpollFd::GetId() const
{
    return "urma_0229";
}
} // namespace diag
