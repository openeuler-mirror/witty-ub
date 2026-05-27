#include "urma_failure_227.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure227> g_urma("urma_227");

bool UrmaFailure227::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure227::GetName() const
{
    return "URMA context、provider操作表、目标Jetty对象、provider未提供unimport_jetty操作实现无效导致解除导入Jetty失败";
}

std::string UrmaFailure227::GetRootCauseDesc() const
{
    return "函数用于解除导入Jetty，调用方传入的URMA "
           "context、provider操作表、目标Jetty对象、provider未提供unimport_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure227::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure227::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure227::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_jetty，Invalid parameter.。";
}

std::string UrmaFailure227::GetId() const
{
    return "urma_227";
}

} // namespace diag
