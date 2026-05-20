#include "urma_failure_253.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure253> g_urma("urma_253");

bool UrmaFailure253::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'set_fd_noblock' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'ret:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure253::GetName() const
{
    return "set_fd_noblock 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure253::GetRootCauseDesc() const
{
    return "set_fd_noblock 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure253::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure253::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure253::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：ret";
}

std::string UrmaFailure253::GetId() const
{
    return "urma_253";
}

} // namespace diag
