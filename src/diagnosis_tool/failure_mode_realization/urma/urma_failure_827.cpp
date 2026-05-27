#include "urma_failure_827.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure827> g_urma("urma_827");

bool UrmaFailure827::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_wait_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure827::GetName() const
{
    return "URMA context、provider操作表、provider未提供wait_notify操作实现无效导致等待Notifier失败";
}

std::string UrmaFailure827::GetRootCauseDesc() const
{
    return "函数用于等待Notifier，调用方传入的URMA "
           "context、provider操作表、provider未提供wait_notify操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure827::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure827::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure827::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_wait_notify，Invalid parameter.";
}

std::string UrmaFailure827::GetId() const
{
    return "urma_827";
}

} // namespace diag
