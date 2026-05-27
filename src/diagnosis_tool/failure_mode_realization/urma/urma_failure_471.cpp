#include "urma_failure_471.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure471> g_urma("urma_471");

bool UrmaFailure471::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_smac' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure471::GetName() const
{
    return "URMA context、provider操作表无效导致获取context失败";
}

std::string UrmaFailure471::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA "
           "context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure471::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure471::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure471::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_smac，Invalid parameter.。";
}

std::string UrmaFailure471::GetId() const
{
    return "urma_471";
}

} // namespace diag
