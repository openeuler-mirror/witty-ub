#include "urma_failure_121.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure121> g_urma("urma_121");

bool UrmaFailure121::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unimport_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure121::GetName() const
{
    return "URMA context无效导致解除导入JFR失败";
}

std::string UrmaFailure121::GetRootCauseDesc() const
{
    return "函数用于解除导入JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure121::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure121::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure121::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unimport_jfr，Invalid parameter。";
}

std::string UrmaFailure121::GetId() const
{
    return "urma_121";
}

} // namespace diag
