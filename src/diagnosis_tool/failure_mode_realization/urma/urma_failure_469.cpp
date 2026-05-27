#include "urma_failure_469.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure469> g_urma("urma_469");

bool UrmaFailure469::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_ip_by_eid' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure469::GetName() const
{
    return "URMA context、provider操作表无效导致获取EID失败";
}

std::string UrmaFailure469::GetRootCauseDesc() const
{
    return "函数用于获取EID，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure469::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure469::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure469::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_ip_by_eid，Invalid parameter.。";
}

std::string UrmaFailure469::GetId() const
{
    return "urma_469";
}

} // namespace diag
