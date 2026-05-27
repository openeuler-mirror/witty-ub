#include "urma_failure_855.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure855> g_urma("urma_855");

bool UrmaFailure855::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure855::GetName() const
{
    return "确认JFC所需输入对象无效导致确认JFC失败";
}

std::string UrmaFailure855::GetRootCauseDesc() const
{
    return "函数用于确认JFC，调用方传入的确认JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure855::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure855::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure855::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ack_jfc，Invalid parameter.";
}

std::string UrmaFailure855::GetId() const
{
    return "urma_855";
}

} // namespace diag
