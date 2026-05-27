#include "urma_failure_176.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure176> g_urma("urma_176");

bool UrmaFailure176::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_tp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed in ioctl get_tp_attr, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure176::GetName() const
{
    return "获取ioctl的ioctl调用返回失败";
}

std::string UrmaFailure176::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure176::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure176::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure176::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_tp_attr，Failed in ioctl get_tp_attr, ret:";
}

std::string UrmaFailure176::GetId() const
{
    return "urma_176";
}

} // namespace diag
