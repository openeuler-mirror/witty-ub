#include "urma_failure_667.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure667> g_urma("urma_667");

bool UrmaFailure667::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_ioctl_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'get async event ioctl failed, ret:' | "
        "grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure667::GetName() const
{
    return "urma_ioctl_get_async_event 导入 Jetty ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure667::GetRootCauseDesc() const
{
    return "urma_ioctl_get_async_event 通过 fd 向内核驱动下发导入 Jetty请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 异步事件 状态。";
}

RootCause UrmaFailure667::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure667::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure667::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：get async event ioctl failed, ret:, errno";
}

std::string UrmaFailure667::GetId() const
{
    return "urma_667";
}

} // namespace diag
