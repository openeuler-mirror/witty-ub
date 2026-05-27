#include "urma_failure_538.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure538> g_urma("urma_538");

bool UrmaFailure538::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unregister_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure538::GetName() const
{
    return "URMA context、设备对象、Segment对象无效导致注销Segment失败";
}

std::string UrmaFailure538::GetRootCauseDesc() const
{
    return "函数用于注销Segment，调用方传入的URMA "
           "context、设备对象、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure538::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure538::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure538::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unregister_seg，Invalid parameter.";
}

std::string UrmaFailure538::GetId() const
{
    return "urma_538";
}

} // namespace diag
