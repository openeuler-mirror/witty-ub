#include "urma_0041_init_slave_context_fd_failed_add_fd_errno.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0041InitSlaveContextFdFailedAddFdErrno> g_urma("urma_0041");

bool Urma0041InitSlaveContextFdFailedAddFdErrno::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to add fd: %, errno: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0041InitSlaveContextFdFailedAddFdErrno::GetName() const
{
    return "init_slave_context_fd failed to add fd: %, errno: %.";
}

std::string Urma0041InitSlaveContextFdFailedAddFdErrno::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `epoll_ctl(bond_ctx->v_ctx.async_fd, EPOLL_CTL_ADD, fd, &ev) != 0`；该路径返回 0";
}

RootCause Urma0041InitSlaveContextFdFailedAddFdErrno::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0041InitSlaveContextFdFailedAddFdErrno::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0041InitSlaveContextFdFailedAddFdErrno::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to add fd: %, errno: %.";
}

std::string Urma0041InitSlaveContextFdFailedAddFdErrno::GetId() const
{
    return "urma_0041";
}
} // namespace diag
