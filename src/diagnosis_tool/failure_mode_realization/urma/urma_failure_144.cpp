#include "urma_failure_144.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure144> g_urma("urma_144");

bool UrmaFailure144::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure144::GetName() const
{
    return "URMA context无效导致删除Jetty失败";
}

std::string UrmaFailure144::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure144::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure144::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure144::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jetty_grp，Invalid parameter";
}

std::string UrmaFailure144::GetId() const
{
    return "urma_144";
}

} // namespace diag
