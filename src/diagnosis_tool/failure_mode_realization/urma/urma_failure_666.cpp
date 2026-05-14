#include "urma_failure_666.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure666> g_urma("urma_666");

bool UrmaFailure666::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_ioctl_wait_jfc' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'wait jfc ioctl failed, ret:, errno')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure666::GetName() const
{
    return "urma_ioctl_wait_jfc 等待 JFC 完成事件 ioctl 下发内核驱动失败导致用户态操作中断";
}

std::string UrmaFailure666::GetRootCauseDesc() const
{
    return "urma_ioctl_wait_jfc 通过 fd 向内核驱动下发等待 JFC 完成事件请求时，ioctl "
           "返回失败，说明内核驱动没有完成对应控制面动作，用户态无法取得或更新 JFC 状态。";
}

RootCause UrmaFailure666::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure666::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure666::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：wait jfc ioctl failed, ret:, errno";
}

std::string UrmaFailure666::GetId() const
{
    return "urma_666";
}

} // namespace diag
