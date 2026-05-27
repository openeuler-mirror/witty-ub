#include "urma_failure_442.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure442> g_urma("urma_442");

bool UrmaFailure442::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_async_event' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure442::GetName() const
{
    return "URMA context无效导致获取JFC失败";
}

std::string UrmaFailure442::GetRootCauseDesc() const
{
    return "函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure442::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure442::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure442::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_async_event，Invalid parameter。";
}

std::string UrmaFailure442::GetId() const
{
    return "urma_442";
}

} // namespace diag
