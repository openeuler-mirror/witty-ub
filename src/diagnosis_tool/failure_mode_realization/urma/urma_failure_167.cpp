#include "urma_failure_167.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure167> g_urma("urma_167");

bool UrmaFailure167::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unimport_jetty_async' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure167::GetName() const
{
    return "URMA context、目标Jetty对象无效导致解除导入Jetty失败";
}

std::string UrmaFailure167::GetRootCauseDesc() const
{
    return "函数用于解除导入Jetty，调用方传入的URMA "
           "context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure167::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure167::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure167::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_unimport_jetty_async，Invalid parameter";
}

std::string UrmaFailure167::GetId() const
{
    return "urma_167";
}

} // namespace diag
