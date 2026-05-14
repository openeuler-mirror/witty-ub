#include "urma_failure_623.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure623> g_urma("urma_623");

bool UrmaFailure623::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_get_async_event' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'bondp get error epoll_event: 0x')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure623::GetName() const
{
    return "bondp_get_async_event 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure623::GetRootCauseDesc() const
{
    return "bondp_get_async_event 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure623::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure623::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure623::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：bondp get error epoll_event: 0x";
}

std::string UrmaFailure623::GetId() const
{
    return "urma_623";
}

} // namespace diag
