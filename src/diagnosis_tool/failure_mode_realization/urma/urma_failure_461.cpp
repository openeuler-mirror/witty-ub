#include "urma_failure_461.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure461> g_urma("urma_461");

bool UrmaFailure461::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure461::GetName() const
{
    return "URMA context、provider操作表、JFR对象、provider未提供get_jfr_opt操作实现无效导致获取JFR失败";
}

std::string UrmaFailure461::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象、provider未提供get_jfr_"
           "opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure461::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure461::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure461::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure461::GetId() const
{
    return "urma_461";
}

} // namespace diag
