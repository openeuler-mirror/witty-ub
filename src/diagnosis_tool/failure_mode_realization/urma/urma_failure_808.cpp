#include "urma_failure_808.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure808> g_urma("urma_808");

bool UrmaFailure808::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_ctrlplane_compat' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure808::GetName() const
{
    return "URMA context、provider操作表无效导致导入Jetty失败";
}

std::string UrmaFailure808::GetRootCauseDesc() const
{
    return "函数用于导入Jetty，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure808::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure808::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure808::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_ctrlplane_compat，Invalid parameter.";
}

std::string UrmaFailure808::GetId() const
{
    return "urma_808";
}

} // namespace diag
