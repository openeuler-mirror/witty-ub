#include "urma_failure_687.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure687> g_urma("urma_687");

bool UrmaFailure687::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_notifier' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure687::GetName() const
{
    return "URMA context、provider操作表无效导致删除Notifier失败";
}

std::string UrmaFailure687::GetRootCauseDesc() const
{
    return "函数用于删除Notifier，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure687::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure687::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure687::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_notifier，Invalid parameter.。";
}

std::string UrmaFailure687::GetId() const
{
    return "urma_687";
}

} // namespace diag
