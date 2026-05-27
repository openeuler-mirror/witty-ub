#include "urma_failure_399.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure399> g_urma("urma_399");

bool UrmaFailure399::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure399::GetName() const
{
    return "URMA context、provider操作表、JFR对象无效导致分配JFR失败";
}

std::string UrmaFailure399::GetRootCauseDesc() const
{
    return "函数用于分配JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure399::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure399::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure399::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfr，Invalid parameter, trans_mode:";
}

std::string UrmaFailure399::GetId() const
{
    return "urma_399";
}

} // namespace diag
