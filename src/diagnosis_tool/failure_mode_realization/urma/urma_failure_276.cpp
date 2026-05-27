#include "urma_failure_276.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure276> g_urma("urma_276");

bool UrmaFailure276::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure276::GetName() const
{
    return "provider操作表、Jetty对象无效导致激活Jetty失败";
}

std::string UrmaFailure276::GetRootCauseDesc() const
{
    return "函数用于激活Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure276::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure276::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure276::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，Invalid parameter.。";
}

std::string UrmaFailure276::GetId() const
{
    return "urma_276";
}

} // namespace diag
