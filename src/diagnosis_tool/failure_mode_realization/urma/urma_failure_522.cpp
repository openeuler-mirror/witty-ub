#include "urma_failure_522.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure522> g_urma("urma_522");

bool UrmaFailure522::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_register_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure522::GetName() const
{
    return "URMA context无效导致注册Segment失败";
}

std::string UrmaFailure522::GetRootCauseDesc() const
{
    return "函数用于注册Segment，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure522::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure522::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure522::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_register_seg，Invalid parameter";
}

std::string UrmaFailure522::GetId() const
{
    return "urma_522";
}

} // namespace diag
