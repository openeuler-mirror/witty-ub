#include "urma_failure_686.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure686> g_urma("urma_686");

bool UrmaFailure686::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure686::GetName() const
{
    return "URMA context、设备对象、provider操作表无效导致删除context失败";
}

std::string UrmaFailure686::GetRootCauseDesc() const
{
    return "函数用于删除context，调用方传入的URMA "
           "context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure686::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure686::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure686::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_context，Invalid parameter.";
}

std::string UrmaFailure686::GetId() const
{
    return "urma_686";
}

} // namespace diag
