#include "urma_failure_132.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure132> g_urma("urma_132");

bool UrmaFailure132::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_query_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure132::GetName() const
{
    return "Jetty对象无效导致查询Jetty失败";
}

std::string UrmaFailure132::GetRootCauseDesc() const
{
    return "函数用于查询Jetty，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure132::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure132::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure132::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_jetty，Invalid parameter。";
}

std::string UrmaFailure132::GetId() const
{
    return "urma_132";
}

} // namespace diag
