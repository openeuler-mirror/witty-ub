#include "urma_failure_487.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure487> g_urma("urma_487");

bool UrmaFailure487::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_log_set_thread_tag' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure487::GetName() const
{
    return "设置线程所需输入对象无效导致设置线程失败";
}

std::string UrmaFailure487::GetRootCauseDesc() const
{
    return "函数用于设置线程，调用方传入的设置线程所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure487::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure487::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure487::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_log_set_thread_tag，Invalid parameter.";
}

std::string UrmaFailure487::GetId() const
{
    return "urma_487";
}

} // namespace diag
