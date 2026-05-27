#include "urma_failure_354.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure354> g_urma("urma_354");

bool UrmaFailure354::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_context' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure354::GetName() const
{
    return "URMA context、设备对象、provider操作表无效导致创建context失败";
}

std::string UrmaFailure354::GetRootCauseDesc() const
{
    return "函数用于创建context，调用方传入的URMA "
           "context、设备对象、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure354::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure354::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure354::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_create_context，Invalid parameter";
}

std::string UrmaFailure354::GetId() const
{
    return "urma_354";
}

} // namespace diag
