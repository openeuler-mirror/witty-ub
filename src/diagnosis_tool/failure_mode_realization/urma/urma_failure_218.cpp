#include "urma_failure_218.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure218> g_urma("urma_218");

bool UrmaFailure218::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_flush_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure218::GetName() const
{
    return "URMA context、Jetty对象无效导致刷出Jetty失败";
}

std::string UrmaFailure218::GetRootCauseDesc() const
{
    return "函数用于刷出Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure218::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure218::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure218::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_flush_jetty，Invalid parameter.。";
}

std::string UrmaFailure218::GetId() const
{
    return "urma_218";
}

} // namespace diag
