#include "urma_failure_449.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure449> g_urma("urma_449");

bool UrmaFailure449::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ioctl_get_async_event' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'get async event ioctl failed, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure449::GetName() const
{
    return "执行get async event驱动命令的ioctl调用返回失败";
}

std::string UrmaFailure449::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交执行get async "
           "event驱动命令请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果。";
}

RootCause UrmaFailure449::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure449::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure449::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ioctl_get_async_event，get async event ioctl failed, ret:，, "
           "errno:。";
}

std::string UrmaFailure449::GetId() const
{
    return "urma_449";
}

} // namespace diag
