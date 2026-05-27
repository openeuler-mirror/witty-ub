#include "urma_failure_499.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure499> g_urma("urma_499");

bool UrmaFailure499::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_perf_thread_exit_cleanup' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Urma perf thread cleanup, thread index' | grep -F 'is invalid.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure499::GetName() const
{
    return "执行线程所需输入对象无效导致初始化线程失败";
}

std::string UrmaFailure499::GetRootCauseDesc() const
{
    return "函数用于初始化线程，调用方传入的执行线程所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure499::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure499::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure499::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_perf_thread_exit_cleanup，Urma perf thread cleanup, thread index，is "
           "invalid.";
}

std::string UrmaFailure499::GetId() const
{
    return "urma_499";
}

} // namespace diag
