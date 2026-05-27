#include "urma_failure_398.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure398> g_urma("urma_398");

bool UrmaFailure398::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure398::GetName() const
{
    return "URMA context、provider操作表、JFR对象无效导致分配JFR失败";
}

std::string UrmaFailure398::GetRootCauseDesc() const
{
    return "函数用于分配JFR，调用方传入的URMA "
           "context、provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure398::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure398::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure398::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfr，Invalid parameter.";
}

std::string UrmaFailure398::GetId() const
{
    return "urma_398";
}

} // namespace diag
