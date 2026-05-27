#include "urma_failure_866.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure866> g_urma("urma_866");

bool UrmaFailure866::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid option name.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure866::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure866::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure866::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure866::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure866::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_context_opt，Invalid option name.";
}

std::string UrmaFailure866::GetId() const
{
    return "urma_866";
}

} // namespace diag
