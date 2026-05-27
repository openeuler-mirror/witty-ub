#include "urma_failure_421.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure421> g_urma("urma_421");

bool UrmaFailure421::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'get_bonding_eid_by_target_eid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid param'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure421::GetName() const
{
    return "获取EID所需输入对象无效导致获取EID失败";
}

std::string UrmaFailure421::GetRootCauseDesc() const
{
    return "函数用于获取EID，调用方传入的获取EID所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure421::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure421::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure421::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：get_bonding_eid_by_target_eid，Invalid param";
}

std::string UrmaFailure421::GetId() const
{
    return "urma_421";
}

} // namespace diag
