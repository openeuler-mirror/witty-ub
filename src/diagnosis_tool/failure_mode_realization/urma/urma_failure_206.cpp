#include "urma_failure_206.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure206> g_urma("urma_206");

bool UrmaFailure206::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure206::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供free_jetty操作实现无效导致释放Jetty失败";
}

std::string UrmaFailure206::GetRootCauseDesc() const
{
    return "函数用于释放Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供free_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure206::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure206::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure206::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_free_jetty，Invalid parameter.。";
}

std::string UrmaFailure206::GetId() const
{
    return "urma_206";
}

} // namespace diag
