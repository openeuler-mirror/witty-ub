#include "urma_failure_581.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure581> g_urma("urma_581");

bool UrmaFailure581::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_write' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure581::GetName() const
{
    return "JFS对象无效导致获取JFS失败";
}

std::string UrmaFailure581::GetRootCauseDesc() const
{
    return "函数用于获取JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure581::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure581::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure581::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_write，Invalid parameter.。";
}

std::string UrmaFailure581::GetId() const
{
    return "urma_581";
}

} // namespace diag
