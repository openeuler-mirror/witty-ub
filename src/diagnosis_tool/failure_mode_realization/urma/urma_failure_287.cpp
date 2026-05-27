#include "urma_failure_287.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure287> g_urma("urma_287");

bool UrmaFailure287::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure287::GetName() const
{
    return "URMA context、provider操作表、provider未提供create_notifier操作实现无效导致去激活Jetty失败";
}

std::string UrmaFailure287::GetRootCauseDesc() const
{
    return "函数用于去激活Jetty，调用方传入的URMA "
           "context、provider操作表、provider未提供create_"
           "notifier操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure287::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure287::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure287::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jetty，Invalid parameter.";
}

std::string UrmaFailure287::GetId() const
{
    return "urma_287";
}

} // namespace diag
