#include "urma_failure_433.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure433> g_urma("urma_433");

bool UrmaFailure433::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid out buffer from kernel.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure433::GetName() const
{
    return "URMA context无效导致获取JFC失败";
}

std::string UrmaFailure433::GetRootCauseDesc() const
{
    return "函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure433::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure433::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure433::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_jfc_opt，Invalid out buffer from kernel.";
}

std::string UrmaFailure433::GetId() const
{
    return "urma_433";
}

} // namespace diag
