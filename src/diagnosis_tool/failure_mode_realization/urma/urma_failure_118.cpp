#include "urma_failure_118.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure118> g_urma("urma_118");

bool UrmaFailure118::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_jfr_ex' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure118::GetName() const
{
    return "URMA context无效导致导入JFR失败";
}

std::string UrmaFailure118::GetRootCauseDesc() const
{
    return "函数用于导入JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure118::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure118::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure118::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_import_jfr_ex，Invalid parameter.";
}

std::string UrmaFailure118::GetId() const
{
    return "urma_118";
}

} // namespace diag
