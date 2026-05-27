#include "urma_failure_225.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure225> g_urma("urma_225");

bool UrmaFailure225::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure225::GetName() const
{
    return "URMA context、provider操作表、目标Jetty对象、provider未提供unimport_jetty操作实现无效导致解除导入Jetty失败";
}

std::string UrmaFailure225::GetRootCauseDesc() const
{
    return "函数用于解除导入Jetty，调用方传入的URMA "
           "context、provider操作表、目标Jetty对象、provider未提供unimport_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure225::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure225::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure225::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unimport_jetty，Invalid parameter.";
}

std::string UrmaFailure225::GetId() const
{
    return "urma_225";
}

} // namespace diag
