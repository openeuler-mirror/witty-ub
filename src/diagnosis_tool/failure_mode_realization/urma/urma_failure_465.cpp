#include "urma_failure_465.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure465> g_urma("urma_465");

bool UrmaFailure465::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_async_event' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure465::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致获取JFR失败";
}

std::string UrmaFailure465::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure465::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure465::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure465::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_async_event，Invalid parameter.。";
}

std::string UrmaFailure465::GetId() const
{
    return "urma_465";
}

} // namespace diag
