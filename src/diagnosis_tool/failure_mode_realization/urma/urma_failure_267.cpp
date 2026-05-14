#include "urma_failure_267.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure267> g_urma("urma_267");

bool UrmaFailure267::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_create_context' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Failed to create epoll')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure267::GetName() const
{
    return "bondp_create_context 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure267::GetRootCauseDesc() const
{
    return "bondp_create_context 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure267::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure267::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure267::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to create epoll";
}

std::string UrmaFailure267::GetId() const
{
    return "urma_267";
}

} // namespace diag
