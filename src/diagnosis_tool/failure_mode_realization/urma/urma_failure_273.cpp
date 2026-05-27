#include "urma_failure_273.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure273> g_urma("urma_273");

bool UrmaFailure273::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure273::GetName() const
{
    return "Jetty对象无效导致获取Jetty失败";
}

std::string UrmaFailure273::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure273::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure273::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure273::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jetty_opt，Invalid parameter.。";
}

std::string UrmaFailure273::GetId() const
{
    return "urma_273";
}

} // namespace diag
