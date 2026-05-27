#include "urma_failure_249.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure249> g_urma("urma_249");

bool UrmaFailure249::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unimport_jetty_async' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure249::GetName() const
{
    return "URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供unimport_jetty_"
           "async操作实现无效导致解除导入Jetty失败";
}

std::string UrmaFailure249::GetRootCauseDesc() const
{
    return "函数用于解除导入Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、目标Jetty对象、provider未提供unimport_jetty_"
           "async操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure249::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure249::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure249::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unimport_jetty_async，Invalid parameter.。";
}

std::string UrmaFailure249::GetId() const
{
    return "urma_249";
}

} // namespace diag
