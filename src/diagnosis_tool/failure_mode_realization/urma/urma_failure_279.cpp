#include "urma_failure_279.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure279> g_urma("urma_279");

bool UrmaFailure279::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure279::GetName() const
{
    return "URMA context无效导致激活Jetty失败";
}

std::string UrmaFailure279::GetRootCauseDesc() const
{
    return "函数用于激活Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure279::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure279::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure279::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，Invalid parameter.。";
}

std::string UrmaFailure279::GetId() const
{
    return "urma_279";
}

} // namespace diag
