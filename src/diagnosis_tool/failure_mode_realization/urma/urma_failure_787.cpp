#include "urma_failure_787.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure787> g_urma("urma_787");

bool UrmaFailure787::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_order_type' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure787::GetName() const
{
    return "URMA context无效导致创建JFS失败";
}

std::string UrmaFailure787::GetRootCauseDesc() const
{
    return "函数用于创建JFS，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure787::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure787::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure787::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_order_type，Invalid parameter.。";
}

std::string UrmaFailure787::GetId() const
{
    return "urma_787";
}

} // namespace diag
