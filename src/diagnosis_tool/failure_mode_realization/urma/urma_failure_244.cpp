#include "urma_failure_244.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure244> g_urma("urma_244");

bool UrmaFailure244::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unadvise_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure244::GetName() const
{
    return "URMA context、provider操作表、provider未提供import_jetty_async操作实现无效导致导入Jetty失败";
}

std::string UrmaFailure244::GetRootCauseDesc() const
{
    return "函数用于导入Jetty，调用方传入的URMA "
           "context、provider操作表、provider未提供import_jetty_"
           "async操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure244::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure244::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure244::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_unadvise_jetty，Invalid parameter.";
}

std::string UrmaFailure244::GetId() const
{
    return "urma_244";
}

} // namespace diag
