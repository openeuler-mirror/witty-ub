#include "urma_failure_575.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure575> g_urma("urma_575");

bool UrmaFailure575::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_write' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure575::GetName() const
{
    return "JFS对象无效导致获取JFS失败";
}

std::string UrmaFailure575::GetRootCauseDesc() const
{
    return "函数用于获取JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure575::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure575::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure575::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_write，Invalid parameter.";
}

std::string UrmaFailure575::GetId() const
{
    return "urma_575";
}

} // namespace diag
