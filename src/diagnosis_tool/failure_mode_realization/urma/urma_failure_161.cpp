#include "urma_failure_161.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure161> g_urma("urma_161");

bool UrmaFailure161::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid out buffer from kernel.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure161::GetName() const
{
    return "URMA context无效导致获取Jetty失败";
}

std::string UrmaFailure161::GetRootCauseDesc() const
{
    return "函数用于获取Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure161::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure161::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure161::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jetty_opt，Invalid out buffer from kernel.。";
}

std::string UrmaFailure161::GetId() const
{
    return "urma_161";
}

} // namespace diag
