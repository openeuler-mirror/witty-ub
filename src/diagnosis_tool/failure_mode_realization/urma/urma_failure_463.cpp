#include "urma_failure_463.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure463> g_urma("urma_463");

bool UrmaFailure463::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_eid_by_ip' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure463::GetName() const
{
    return "URMA context、provider操作表无效导致获取EID失败";
}

std::string UrmaFailure463::GetRootCauseDesc() const
{
    return "函数用于获取EID，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure463::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure463::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure463::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_eid_by_ip，Invalid parameter.";
}

std::string UrmaFailure463::GetId() const
{
    return "urma_463";
}

} // namespace diag
