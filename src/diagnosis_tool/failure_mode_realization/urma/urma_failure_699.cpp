#include "urma_failure_699.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure699> g_urma("urma_699");

bool UrmaFailure699::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_active_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_active_jfr, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure699::GetName() const
{
    return "激活ioctl的ioctl调用返回失败";
}

std::string UrmaFailure699::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交激活ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure699::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure699::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure699::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_active_jfr，ioctl failed in urma_cmd_active_jfr, ret:，, errno:";
}

std::string UrmaFailure699::GetId() const
{
    return "urma_699";
}

} // namespace diag
