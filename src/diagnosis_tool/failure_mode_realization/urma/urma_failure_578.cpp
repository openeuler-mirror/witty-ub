#include "urma_failure_578.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure578> g_urma("urma_578");

bool UrmaFailure578::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_send' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure578::GetName() const
{
    return "JFS对象无效导致获取JFR失败";
}

std::string UrmaFailure578::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure578::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure578::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure578::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_send，Invalid parameter.";
}

std::string UrmaFailure578::GetId() const
{
    return "urma_578";
}

} // namespace diag
