#include "urma_failure_704.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure704> g_urma("urma_704");

bool UrmaFailure704::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ioctl_wait_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'wait notify ioctl failed, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure704::GetName() const
{
    return "执行wait notify驱动命令的ioctl调用返回失败";
}

std::string UrmaFailure704::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交执行wait "
           "notify驱动命令请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。";
}

RootCause UrmaFailure704::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure704::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure704::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ioctl_wait_notify，wait notify ioctl failed, ret:，, errno:";
}

std::string UrmaFailure704::GetId() const
{
    return "urma_704";
}

} // namespace diag
