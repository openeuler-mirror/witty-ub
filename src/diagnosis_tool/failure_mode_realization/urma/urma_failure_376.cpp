#include "urma_failure_376.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure376> g_urma("urma_376");

bool UrmaFailure376::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure376::GetName() const
{
    return "URMA context无效导致创建JFCE失败";
}

std::string UrmaFailure376::GetRootCauseDesc() const
{
    return "函数用于创建JFCE，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure376::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure376::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure376::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_create_jfce，Invalid parameter";
}

std::string UrmaFailure376::GetId() const
{
    return "urma_376";
}

} // namespace diag
