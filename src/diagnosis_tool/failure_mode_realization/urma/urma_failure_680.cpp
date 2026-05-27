#include "urma_failure_680.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure680> g_urma("urma_680");

bool UrmaFailure680::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_notifier' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure680::GetName() const
{
    return "URMA context、provider操作表无效导致删除Notifier失败";
}

std::string UrmaFailure680::GetRootCauseDesc() const
{
    return "函数用于删除Notifier，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure680::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure680::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure680::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_notifier，Invalid parameter.";
}

std::string UrmaFailure680::GetId() const
{
    return "urma_680";
}

} // namespace diag
