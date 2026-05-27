#include "urma_failure_134.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure134> g_urma("urma_134");

bool UrmaFailure134::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jetty_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure134::GetName() const
{
    return "URMA context、Jetty对象无效导致删除Jetty失败";
}

std::string UrmaFailure134::GetRootCauseDesc() const
{
    return "函数用于删除Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure134::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure134::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure134::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jetty_batch，Invalid parameter, index:";
}

std::string UrmaFailure134::GetId() const
{
    return "urma_134";
}

} // namespace diag
