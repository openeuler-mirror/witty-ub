#include "urma_failure_467.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure467> g_urma("urma_467");

bool UrmaFailure467::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_smac' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure467::GetName() const
{
    return "URMA context、provider操作表无效导致获取context失败";
}

std::string UrmaFailure467::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure467::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure467::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure467::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_smac，Invalid parameter.";
}

std::string UrmaFailure467::GetId() const
{
    return "urma_467";
}

} // namespace diag
