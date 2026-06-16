#include "urma_failure_258.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure258> g_urma("urma_258");

bool UrmaFailure258::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure258::GetName() const
{
    return "URMA context、设备对象、provider操作表、Jetty对象无效导致分配Jetty失败";
}

std::string UrmaFailure258::GetRootCauseDesc() const
{
    return "函数用于分配Jetty，调用方传入的URMA "
           "context、设备对象、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure258::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure258::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure258::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_alloc_jetty，Invalid parameter.。";
}

std::string UrmaFailure258::GetId() const
{
    return "urma_258";
}

} // namespace diag
