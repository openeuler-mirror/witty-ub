#include "urma_failure_140.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure140> g_urma("urma_140");

bool UrmaFailure140::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure140::GetName() const
{
    return "URMA context、目标Jetty对象无效导致导入Jetty失败";
}

std::string UrmaFailure140::GetRootCauseDesc() const
{
    return "函数用于导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure140::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure140::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure140::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_import_jetty，Invalid parameter";
}

std::string UrmaFailure140::GetId() const
{
    return "urma_140";
}

} // namespace diag
