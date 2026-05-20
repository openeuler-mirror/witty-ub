#include "urma_failure_545.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure545> g_urma("urma_545");

bool UrmaFailure545::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_ioctl_get_eid_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to open urma cdev with path'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure545::GetName() const
{
    return "urma_ioctl_get_eid_list URMA 控制面命令 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure545::GetRootCauseDesc() const
{
    return "urma_ioctl_get_eid_list 通过 fd 向内核驱动下发URMA 控制面命令请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 设备 状态。";
}

RootCause UrmaFailure545::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure545::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure545::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Failed to open urma cdev with path";
}

std::string UrmaFailure545::GetId() const
{
    return "urma_545";
}

} // namespace diag
