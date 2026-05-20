#include "urma_failure_266.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure266> g_urma("urma_266");

bool UrmaFailure266::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_create_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create context'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure266::GetName() const
{
    return "bondp_create_context 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure266::GetRootCauseDesc() const
{
    return "bondp_create_context 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure266::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure266::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure266::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create context";
}

std::string UrmaFailure266::GetId() const
{
    return "urma_266";
}

} // namespace diag
