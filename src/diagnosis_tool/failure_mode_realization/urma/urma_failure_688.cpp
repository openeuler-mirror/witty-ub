#include "urma_failure_688.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure688> g_urma("urma_688");

bool UrmaFailure688::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_notifier' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure688::GetName() const
{
    return "URMA context、provider操作表、provider未提供delete_notifier操作实现无效导致删除Notifier失败";
}

std::string UrmaFailure688::GetRootCauseDesc() const
{
    return "函数用于删除Notifier，调用方传入的URMA "
           "context、provider操作表、provider未提供delete_"
           "notifier操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure688::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure688::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure688::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_notifier，Invalid parameter.。";
}

std::string UrmaFailure688::GetId() const
{
    return "urma_688";
}

} // namespace diag
