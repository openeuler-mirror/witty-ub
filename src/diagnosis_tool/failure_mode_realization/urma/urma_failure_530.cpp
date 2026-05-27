#include "urma_failure_530.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure530> g_urma("urma_530");

bool UrmaFailure530::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure530::GetName() const
{
    return "URMA context、provider操作表无效导致解除导入Segment失败";
}

std::string UrmaFailure530::GetRootCauseDesc() const
{
    return "函数用于解除导入Segment，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure530::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure530::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure530::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unimport_seg，Invalid parameter.";
}

std::string UrmaFailure530::GetId() const
{
    return "urma_530";
}

} // namespace diag
