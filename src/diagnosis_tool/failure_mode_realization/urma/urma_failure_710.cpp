#include "urma_failure_710.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure710> g_urma("urma_710");

bool UrmaFailure710::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'bondp_remove_p_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Fail to del fd: to epoll fd'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure710::GetName() const
{
    return "bondp_remove_p_jfce 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure710::GetRootCauseDesc() const
{
    return "bondp_remove_p_jfce 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure710::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure710::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure710::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Fail to del fd: to epoll fd";
}

std::string UrmaFailure710::GetId() const
{
    return "urma_710";
}

} // namespace diag
