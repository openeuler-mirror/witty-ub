#include "urma_failure_502.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure502> g_urma("urma_502");

bool UrmaFailure502::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_uasid' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure502::GetName() const
{
    return "URMA context无效导致获取context失败";
}

std::string UrmaFailure502::GetRootCauseDesc() const
{
    return "函数用于获取context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure502::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure502::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure502::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_uasid，Invalid parameter.。";
}

std::string UrmaFailure502::GetId() const
{
    return "urma_502";
}

} // namespace diag
