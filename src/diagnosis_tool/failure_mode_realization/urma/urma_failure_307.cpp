#include "urma_failure_307.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure307> g_urma("urma_307");

bool UrmaFailure307::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_tp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure307::GetName() const
{
    return "URMA context、provider操作表、provider未提供modify_tp操作实现无效导致修改TP失败";
}

std::string UrmaFailure307::GetRootCauseDesc() const
{
    return "函数用于修改TP，调用方传入的URMA "
           "context、provider操作表、provider未提供modify_tp操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure307::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure307::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure307::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_modify_tp，Invalid parameter.";
}

std::string UrmaFailure307::GetId() const
{
    return "urma_307";
}

} // namespace diag
