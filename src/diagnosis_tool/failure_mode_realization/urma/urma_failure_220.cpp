#include "urma_failure_220.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure220> g_urma("urma_220");

bool UrmaFailure220::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_flush_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure220::GetName() const
{
    return "URMA context、provider操作表、目标Jetty对象、provider未提供import_jetty_ex操作实现无效导致刷出Jetty失败";
}

std::string UrmaFailure220::GetRootCauseDesc() const
{
    return "函数用于刷出Jetty，调用方传入的URMA "
           "context、provider操作表、目标Jetty对象、provider未提供import_jetty_"
           "ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure220::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure220::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure220::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_flush_jetty，Invalid parameter.。";
}

std::string UrmaFailure220::GetId() const
{
    return "urma_220";
}

} // namespace diag
