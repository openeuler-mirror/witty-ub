#include "urma_failure_742.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure742> g_urma("urma_742");

bool UrmaFailure742::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_modify_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure742::GetName() const
{
    return "URMA context无效导致修改JFC失败";
}

std::string UrmaFailure742::GetRootCauseDesc() const
{
    return "函数用于修改JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure742::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure742::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure742::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_modify_jfc，Invalid parameter";
}

std::string UrmaFailure742::GetId() const
{
    return "urma_742";
}

} // namespace diag
