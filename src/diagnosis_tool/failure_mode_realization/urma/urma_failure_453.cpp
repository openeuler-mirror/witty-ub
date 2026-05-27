#include "urma_failure_453.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure453> g_urma("urma_453");

bool UrmaFailure453::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_jfs' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure453::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致查询JFS失败";
}

std::string UrmaFailure453::GetRootCauseDesc() const
{
    return "函数用于查询JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure453::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure453::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure453::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_jfs，Invalid parameter.。";
}

std::string UrmaFailure453::GetId() const
{
    return "urma_453";
}

} // namespace diag
