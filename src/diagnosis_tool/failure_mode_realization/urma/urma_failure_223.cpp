#include "urma_failure_223.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure223> g_urma("urma_223");

bool UrmaFailure223::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_flush_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure223::GetName() const
{
    return "URMA context、provider操作表无效导致刷出Jetty失败";
}

std::string UrmaFailure223::GetRootCauseDesc() const
{
    return "函数用于刷出Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure223::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure223::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure223::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_flush_jetty，Invalid parameter.。";
}

std::string UrmaFailure223::GetId() const
{
    return "urma_223";
}

} // namespace diag
