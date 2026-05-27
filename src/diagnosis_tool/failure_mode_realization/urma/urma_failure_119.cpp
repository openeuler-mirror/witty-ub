#include "urma_failure_119.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure119> g_urma("urma_119");

bool UrmaFailure119::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure119::GetName() const
{
    return "URMA context无效导致导入JFR失败";
}

std::string UrmaFailure119::GetRootCauseDesc() const
{
    return "函数用于导入JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure119::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure119::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure119::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_jfr，Invalid parameter。";
}

std::string UrmaFailure119::GetId() const
{
    return "urma_119";
}

} // namespace diag
