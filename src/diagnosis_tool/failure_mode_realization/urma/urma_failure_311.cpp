#include "urma_failure_311.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure311> g_urma("urma_311");

bool UrmaFailure311::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_tp_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure311::GetName() const
{
    return "URMA context、provider操作表无效导致设置TP失败";
}

std::string UrmaFailure311::GetRootCauseDesc() const
{
    return "函数用于设置TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure311::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure311::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure311::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_tp_attr，Invalid parameter.";
}

std::string UrmaFailure311::GetId() const
{
    return "urma_311";
}

} // namespace diag
