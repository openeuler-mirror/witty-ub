#include "urma_failure_470.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure470> g_urma("urma_470");

bool UrmaFailure470::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_dmac' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure470::GetName() const
{
    return "URMA context、provider操作表、provider未提供get_dmac操作实现无效导致获取context失败";
}

std::string UrmaFailure470::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA "
           "context、provider操作表、provider未提供get_dmac操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure470::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure470::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure470::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_dmac，Invalid parameter.";
}

std::string UrmaFailure470::GetId() const
{
    return "urma_470";
}

} // namespace diag
