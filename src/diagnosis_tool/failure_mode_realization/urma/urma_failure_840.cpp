#include "urma_failure_840.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure840> g_urma("urma_840");

bool UrmaFailure840::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure840::GetName() const
{
    return "URMA context、provider操作表无效导致确认context失败";
}

std::string UrmaFailure840::GetRootCauseDesc() const
{
    return "函数用于确认context，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure840::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure840::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure840::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_notify，Invalid parameter.。";
}

std::string UrmaFailure840::GetId() const
{
    return "urma_840";
}

} // namespace diag
