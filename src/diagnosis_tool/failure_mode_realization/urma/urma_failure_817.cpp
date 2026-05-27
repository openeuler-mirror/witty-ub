#include "urma_failure_817.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure817> g_urma("urma_817");

bool UrmaFailure817::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure817::GetName() const
{
    return "URMA context、provider操作表、JFR对象无效导致激活JFR失败";
}

std::string UrmaFailure817::GetRootCauseDesc() const
{
    return "函数用于激活JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure817::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure817::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure817::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfr，Invalid parameter, trans_mode:";
}

std::string UrmaFailure817::GetId() const
{
    return "urma_817";
}

} // namespace diag
