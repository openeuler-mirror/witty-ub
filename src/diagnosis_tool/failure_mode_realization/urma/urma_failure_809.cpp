#include "urma_failure_809.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure809> g_urma("urma_809");

bool UrmaFailure809::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_ctrlplane_compat' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure809::GetName() const
{
    return "URMA context、provider操作表、provider未提供import_jfr_ex操作实现无效导致导入JFR失败";
}

std::string UrmaFailure809::GetRootCauseDesc() const
{
    return "函数用于导入JFR，调用方传入的URMA "
           "context、provider操作表、provider未提供import_jfr_ex操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure809::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure809::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure809::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_ctrlplane_compat，Invalid parameter.";
}

std::string UrmaFailure809::GetId() const
{
    return "urma_809";
}

} // namespace diag
