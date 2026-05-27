#include "urma_failure_609.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure609> g_urma("urma_609");

bool UrmaFailure609::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure609::GetName() const
{
    return "URMA context无效导致删除context失败";
}

std::string UrmaFailure609::GetRootCauseDesc() const
{
    return "函数用于删除context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure609::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure609::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure609::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_context，Invalid parameter";
}

std::string UrmaFailure609::GetId() const
{
    return "urma_609";
}

} // namespace diag
