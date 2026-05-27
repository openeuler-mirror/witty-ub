#include "urma_failure_534.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure534> g_urma("urma_534");

bool UrmaFailure534::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_seg' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure534::GetName() const
{
    return "URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_token_id_"
           "ex操作实现无效导致解除导入Segment失败";
}

std::string UrmaFailure534::GetRootCauseDesc() const
{
    return "函数用于解除导入Segment，调用方传入的URMA "
           "context、设备对象、sysfs设备信息、provider操作表、provider未提供alloc_token_id_"
           "ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure534::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure534::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure534::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unimport_seg，Invalid parameter.";
}

std::string UrmaFailure534::GetId() const
{
    return "urma_534";
}

} // namespace diag
