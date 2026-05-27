#include "urma_failure_730.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure730> g_urma("urma_730");

bool UrmaFailure730::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_ack_async_event' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure730::GetName() const
{
    return "确认URMA资源所需输入对象无效导致确认URMA资源失败";
}

std::string UrmaFailure730::GetRootCauseDesc() const
{
    return "函数用于确认URMA资源，调用方传入的确认URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure730::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure730::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure730::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_ack_async_event，Invalid parameter。";
}

std::string UrmaFailure730::GetId() const
{
    return "urma_730";
}

} // namespace diag
