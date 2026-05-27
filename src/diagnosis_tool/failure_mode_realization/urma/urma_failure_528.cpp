#include "urma_failure_528.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure528> g_urma("urma_528");

bool UrmaFailure528::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure528::GetName() const
{
    return "URMA context、设备对象、provider操作表、Segment对象无效导致解除导入Segment失败";
}

std::string UrmaFailure528::GetRootCauseDesc() const
{
    return "函数用于解除导入Segment，调用方传入的URMA "
           "context、设备对象、provider操作表、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure528::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure528::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure528::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unimport_seg，Invalid parameter.";
}

std::string UrmaFailure528::GetId() const
{
    return "urma_528";
}

} // namespace diag
