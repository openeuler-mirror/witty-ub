#include "urma_failure_254.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure254> g_urma("urma_254");

bool UrmaFailure254::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'init_slave_context_fd' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'failed to add fd:' | grep -F ', errno:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure254::GetName() const
{
    return "init_slave_context_fd 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure254::GetRootCauseDesc() const
{
    return "init_slave_context_fd 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure254::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure254::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure254::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：failed to add fd: , errno";
}

std::string UrmaFailure254::GetId() const
{
    return "urma_254";
}

} // namespace diag
