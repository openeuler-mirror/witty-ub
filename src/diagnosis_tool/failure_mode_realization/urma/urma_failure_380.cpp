#include "urma_failure_380.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure380> g_urma("urma_380");

bool UrmaFailure380::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_notifier' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure380::GetName() const
{
    return "URMA context、Jetty对象无效导致创建Notifier失败";
}

std::string UrmaFailure380::GetRootCauseDesc() const
{
    return "函数用于创建Notifier，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure380::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure380::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure380::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_create_notifier，Invalid parameter";
}

std::string UrmaFailure380::GetId() const
{
    return "urma_380";
}

} // namespace diag
