#include "urma_failure_443.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure443> g_urma("urma_443");

bool UrmaFailure443::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_smac' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure443::GetName() const
{
    return "URMA context无效导致获取context失败";
}

std::string UrmaFailure443::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure443::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure443::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure443::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_smac，Invalid parameter.";
}

std::string UrmaFailure443::GetId() const
{
    return "urma_443";
}

} // namespace diag
