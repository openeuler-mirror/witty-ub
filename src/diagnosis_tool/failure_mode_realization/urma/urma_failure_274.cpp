#include "urma_failure_274.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure274> g_urma("urma_274");

bool UrmaFailure274::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure274::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供get_jetty_opt操作实现无效导致获取Jetty失败";
}

std::string UrmaFailure274::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供get_jetty_"
           "opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure274::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure274::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure274::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jetty_opt，Invalid parameter.。";
}

std::string UrmaFailure274::GetId() const
{
    return "urma_274";
}

} // namespace diag
