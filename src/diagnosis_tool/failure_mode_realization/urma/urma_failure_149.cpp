#include "urma_failure_149.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure149> g_urma("urma_149");

bool UrmaFailure149::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure149::GetName() const
{
    return "URMA context、Jetty对象无效导致释放Jetty失败";
}

std::string UrmaFailure149::GetRootCauseDesc() const
{
    return "函数用于释放Jetty，调用方传入的URMA context、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure149::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure149::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure149::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jetty，Invalid parameter。";
}

std::string UrmaFailure149::GetId() const
{
    return "urma_149";
}

} // namespace diag
