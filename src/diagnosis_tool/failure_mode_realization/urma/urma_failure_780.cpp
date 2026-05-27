#include "urma_failure_780.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure780> g_urma("urma_780");

bool UrmaFailure780::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure780::GetName() const
{
    return "provider操作表无效导致激活JFC失败";
}

std::string UrmaFailure780::GetRootCauseDesc() const
{
    return "函数用于激活JFC，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure780::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure780::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure780::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jfc，Invalid parameter.。";
}

std::string UrmaFailure780::GetId() const
{
    return "urma_780";
}

} // namespace diag
