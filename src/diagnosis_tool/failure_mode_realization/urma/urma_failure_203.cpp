#include "urma_failure_203.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure203> g_urma("urma_203");

bool UrmaFailure203::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure203::GetName() const
{
    return "URMA context、provider操作表、Jetty对象无效导致释放Jetty失败";
}

std::string UrmaFailure203::GetRootCauseDesc() const
{
    return "函数用于释放Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure203::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure203::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure203::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jetty，Invalid parameter.。";
}

std::string UrmaFailure203::GetId() const
{
    return "urma_203";
}

} // namespace diag
