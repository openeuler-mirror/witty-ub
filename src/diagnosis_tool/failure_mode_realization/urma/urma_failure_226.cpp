#include "urma_failure_226.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure226> g_urma("urma_226");

bool UrmaFailure226::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure226::GetName() const
{
    return "URMA context、provider操作表、目标Jetty对象无效导致解除导入Jetty失败";
}

std::string UrmaFailure226::GetRootCauseDesc() const
{
    return "函数用于解除导入Jetty，调用方传入的URMA "
           "context、provider操作表、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure226::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure226::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure226::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_jetty，Invalid parameter.。";
}

std::string UrmaFailure226::GetId() const
{
    return "urma_226";
}

} // namespace diag
