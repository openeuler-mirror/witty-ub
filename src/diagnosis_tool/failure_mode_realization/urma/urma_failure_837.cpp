#include "urma_failure_837.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure837> g_urma("urma_837");

bool UrmaFailure837::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_wait_notify' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure837::GetName() const
{
    return "URMA context、provider操作表、provider未提供ack_notify操作实现无效导致等待Notifier失败";
}

std::string UrmaFailure837::GetRootCauseDesc() const
{
    return "函数用于等待Notifier，调用方传入的URMA "
           "context、provider操作表、provider未提供ack_notify操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure837::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure837::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure837::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_wait_notify，Invalid parameter.。";
}

std::string UrmaFailure837::GetId() const
{
    return "urma_837";
}

} // namespace diag
