#include "urma_failure_178.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure178> g_urma("urma_178");

bool UrmaFailure178::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure178::GetName() const
{
    return "URMA context、provider操作表无效导致解除导入JFR失败";
}

std::string UrmaFailure178::GetRootCauseDesc() const
{
    return "函数用于解除导入JFR，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure178::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure178::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure178::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unimport_jfr，Invalid parameter.";
}

std::string UrmaFailure178::GetId() const
{
    return "urma_178";
}

} // namespace diag
