#include "urma_failure_418.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure418> g_urma("urma_418");

bool UrmaFailure418::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_get_async_event' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure418::GetName() const
{
    return "URMA context无效导致获取EID失败";
}

std::string UrmaFailure418::GetRootCauseDesc() const
{
    return "函数用于获取EID，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure418::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure418::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure418::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_get_async_event，Invalid parameter。";
}

std::string UrmaFailure418::GetId() const
{
    return "urma_418";
}

} // namespace diag
