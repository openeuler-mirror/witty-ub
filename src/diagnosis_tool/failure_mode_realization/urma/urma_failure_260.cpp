#include "urma_failure_260.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure260> g_urma("urma_260");

bool UrmaFailure260::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure260::GetName() const
{
    return "URMA context、provider操作表、provider未提供alloc_jetty操作实现无效导致分配Jetty失败";
}

std::string UrmaFailure260::GetRootCauseDesc() const
{
    return "函数用于分配Jetty，调用方传入的URMA "
           "context、provider操作表、provider未提供alloc_jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure260::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure260::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure260::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jetty，Invalid parameter.";
}

std::string UrmaFailure260::GetId() const
{
    return "urma_260";
}

} // namespace diag
