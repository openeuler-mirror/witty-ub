#include "urma_failure_094.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure094> g_urma("urma_094");

bool UrmaFailure094::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'failed to get invalid jetty.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure094::GetName() const
{
    return "URMA context、Jetty对象无效导致获取Jetty失败";
}

std::string UrmaFailure094::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure094::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure094::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure094::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_get_async_event，failed to get invalid jetty.。";
}

std::string UrmaFailure094::GetId() const
{
    return "urma_094";
}

} // namespace diag
