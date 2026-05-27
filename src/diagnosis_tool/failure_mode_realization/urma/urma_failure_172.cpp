#include "urma_failure_172.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure172> g_urma("urma_172");

bool UrmaFailure172::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_tp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid tp_attr bytes.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure172::GetName() const
{
    return "URMA context无效导致设置TP失败";
}

std::string UrmaFailure172::GetRootCauseDesc() const
{
    return "函数用于设置TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure172::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure172::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure172::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_tp_attr，Invalid tp_attr bytes.";
}

std::string UrmaFailure172::GetId() const
{
    return "urma_172";
}

} // namespace diag
