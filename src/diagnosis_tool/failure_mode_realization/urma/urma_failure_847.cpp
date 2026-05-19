#include "urma_failure_847.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure847> g_urma("urma_847");

bool UrmaFailure847::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'bondp_insert_p_jfce' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'Fail to add fd:' | grep -F 'to epoll fd')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure847::GetName() const
{
    return "bondp_insert_p_jfce 管理 epoll fd 失败导致 JFCE 事件聚合不可用";
}

std::string UrmaFailure847::GetRootCauseDesc() const
{
    return "bondp_insert_p_jfce 在 bond 模式下需要把物理 JFCE fd 加入或移出虚拟 JFCE 的 epoll 集合，但 epoll "
           "系统调用失败，完成事件无法被统一监听和分发。";
}

RootCause UrmaFailure847::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure847::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure847::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Fail to add fd: to epoll fd";
}

std::string UrmaFailure847::GetId() const
{
    return "urma_847";
}

} // namespace diag
