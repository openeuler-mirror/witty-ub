#include "urma_0214_bondp_insert_p_jfce_fail_add_fd_epoll_fd.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0214BondpInsertPJfceFailAddFdEpollFd> g_urma("urma_0214");

bool Urma0214BondpInsertPJfceFailAddFdEpollFd::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Fail to add fd:% to epoll fd:%."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0214BondpInsertPJfceFailAddFdEpollFd::GetName() const
{
    return "bondp_insert_p_jfce Fail to add fd:% to epoll fd:%.";
}

std::string Urma0214BondpInsertPJfceFailAddFdEpollFd::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `epoll_ctl(v_jfce->fd, EPOLL_CTL_ADD, p_jfce->fd, &ev) != 0`；该路径返回 URMA_FAIL";
}

RootCause Urma0214BondpInsertPJfceFailAddFdEpollFd::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0214BondpInsertPJfceFailAddFdEpollFd::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0214BondpInsertPJfceFailAddFdEpollFd::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Fail to add fd:% to epoll fd:%.";
}

std::string Urma0214BondpInsertPJfceFailAddFdEpollFd::GetId() const
{
    return "urma_0214";
}
} // namespace diag
