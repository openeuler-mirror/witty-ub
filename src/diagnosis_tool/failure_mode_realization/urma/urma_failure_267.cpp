#include "urma_failure_267.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure267> g_urma("urma_267");

bool UrmaFailure267::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to exec urma_jetty_set_options.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure267::GetName() const
{
    return "设置Jetty过程中依赖步骤失败";
}

std::string UrmaFailure267::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure267::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure267::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure267::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jetty_opt，Failed to exec urma_jetty_set_options.";
}

std::string UrmaFailure267::GetId() const
{
    return "urma_267";
}

} // namespace diag
