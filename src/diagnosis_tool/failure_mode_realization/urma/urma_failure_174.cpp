#include "urma_failure_174.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure174> g_urma("urma_174");

bool UrmaFailure174::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_tp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure174::GetName() const
{
    return "URMA context无效导致获取TP失败";
}

std::string UrmaFailure174::GetRootCauseDesc() const
{
    return "函数用于获取TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure174::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure174::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure174::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_tp_attr，Invalid parameter.";
}

std::string UrmaFailure174::GetId() const
{
    return "urma_174";
}

} // namespace diag
