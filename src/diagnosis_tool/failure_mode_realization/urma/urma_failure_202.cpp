#include "urma_failure_202.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure202> g_urma("urma_202");

bool UrmaFailure202::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure202::GetName() const
{
    return "URMA context、provider操作表、Jetty对象、provider未提供query_jetty操作实现无效导致查询Jetty失败";
}

std::string UrmaFailure202::GetRootCauseDesc() const
{
    return "函数用于查询Jetty，调用方传入的URMA "
           "context、provider操作表、Jetty对象、provider未提供query_"
           "jetty操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure202::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure202::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure202::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jetty，Invalid parameter.。";
}

std::string UrmaFailure202::GetId() const
{
    return "urma_202";
}

} // namespace diag
