#include "urma_failure_454.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure454> g_urma("urma_454");

bool UrmaFailure454::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure454::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供query_jfs操作实现无效导致查询JFS失败";
}

std::string UrmaFailure454::GetRootCauseDesc() const
{
    return "函数用于查询JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供query_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure454::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure454::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure454::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jfs，Invalid parameter.。";
}

std::string UrmaFailure454::GetId() const
{
    return "urma_454";
}

} // namespace diag
