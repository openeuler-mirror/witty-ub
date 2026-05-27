#include "urma_failure_814.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure814> g_urma("urma_814");

bool UrmaFailure814::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure814::GetName() const
{
    return "URMA context、provider操作表、JFR对象、provider未提供set_jfr_opt操作实现无效导致设置JFR失败";
}

std::string UrmaFailure814::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象、provider未提供set_jfr_"
           "opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure814::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure814::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure814::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfr_opt，Invalid parameter.";
}

std::string UrmaFailure814::GetId() const
{
    return "urma_814";
}

} // namespace diag
