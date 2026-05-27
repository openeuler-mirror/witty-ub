#include "urma_failure_758.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure758> g_urma("urma_758");

bool UrmaFailure758::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_wait_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure758::GetName() const
{
    return "URMA context无效导致等待ioctl失败";
}

std::string UrmaFailure758::GetRootCauseDesc() const
{
    return "函数用于等待ioctl，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure758::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure758::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure758::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_wait_notify，Invalid parameter";
}

std::string UrmaFailure758::GetId() const
{
    return "urma_758";
}

} // namespace diag
