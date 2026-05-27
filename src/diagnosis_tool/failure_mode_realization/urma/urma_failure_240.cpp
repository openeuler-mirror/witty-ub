#include "urma_failure_240.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure240> g_urma("urma_240");

bool UrmaFailure240::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_advise_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure240::GetName() const
{
    return "URMA context、设备对象、Jetty对象、目标Jetty对象无效导致执行Jetty失败";
}

std::string UrmaFailure240::GetRootCauseDesc() const
{
    return "函数用于执行Jetty，调用方传入的URMA "
           "context、设备对象、Jetty对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure240::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure240::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure240::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_advise_jetty，Invalid parameter.。";
}

std::string UrmaFailure240::GetId() const
{
    return "urma_240";
}

} // namespace diag
