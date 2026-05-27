#include "urma_failure_731.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure731> g_urma("urma_731");

bool UrmaFailure731::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_set_bonding_mode' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid context.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure731::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure731::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure731::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure731::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure731::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_set_bonding_mode，Invalid context.。";
}

std::string UrmaFailure731::GetId() const
{
    return "urma_731";
}

} // namespace diag
