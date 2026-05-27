#include "urma_failure_293.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure293> g_urma("urma_293");

bool UrmaFailure293::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure293::GetName() const
{
    return "URMA context无效导致删除Jetty失败";
}

std::string UrmaFailure293::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure293::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure293::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure293::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty_grp，Invalid parameter.";
}

std::string UrmaFailure293::GetId() const
{
    return "urma_293";
}

} // namespace diag
