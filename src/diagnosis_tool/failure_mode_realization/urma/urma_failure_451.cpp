#include "urma_failure_451.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure451> g_urma("urma_451");

bool UrmaFailure451::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfc_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure451::GetName() const
{
    return "URMA context、provider操作表、provider未提供get_jfc_opt操作实现无效导致获取JFC失败";
}

std::string UrmaFailure451::GetRootCauseDesc() const
{
    return "函数用于获取JFC，调用方传入的URMA "
           "context、provider操作表、provider未提供get_jfc_opt操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure451::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure451::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure451::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_jfc_opt，Invalid parameter.。";
}

std::string UrmaFailure451::GetId() const
{
    return "urma_451";
}

} // namespace diag
