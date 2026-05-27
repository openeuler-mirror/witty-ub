#include "urma_failure_592.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure592> g_urma("urma_592");

bool UrmaFailure592::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_step_perf' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Urma perf type' | grep -F 'is invalid.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure592::GetName() const
{
    return "执行URMA资源所需输入对象无效导致执行context失败";
}

std::string UrmaFailure592::GetRootCauseDesc() const
{
    return "函数用于执行context，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure592::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure592::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure592::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_step_perf，Urma perf type，is invalid.。";
}

std::string UrmaFailure592::GetId() const
{
    return "urma_592";
}

} // namespace diag
