#include "urma_failure_864.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure864> g_urma("urma_864");

bool UrmaFailure864::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid option value.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure864::GetName() const
{
    return "URMA context、设备对象、provider操作表无效导致设置context失败";
}

std::string UrmaFailure864::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA "
           "context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure864::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure864::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure864::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_context_opt，Invalid option value.";
}

std::string UrmaFailure864::GetId() const
{
    return "urma_864";
}

} // namespace diag
