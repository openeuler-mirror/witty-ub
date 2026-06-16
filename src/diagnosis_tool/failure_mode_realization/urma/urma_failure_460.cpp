#include "urma_failure_460.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure460> g_urma("urma_460");

bool UrmaFailure460::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure460::GetName() const
{
    return "provider操作表、JFR对象无效导致获取JFR失败";
}

std::string UrmaFailure460::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的provider操作表、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure460::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure460::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure460::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfr_opt，Invalid parameter.。";
}

std::string UrmaFailure460::GetId() const
{
    return "urma_460";
}

} // namespace diag
