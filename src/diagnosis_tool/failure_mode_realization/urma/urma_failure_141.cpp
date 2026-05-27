#include "urma_failure_141.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure141> g_urma("urma_141");

bool UrmaFailure141::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_jetty_ex' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure141::GetName() const
{
    return "URMA context、目标Jetty对象无效导致导入Jetty失败";
}

std::string UrmaFailure141::GetRootCauseDesc() const
{
    return "函数用于导入Jetty，调用方传入的URMA context、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure141::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure141::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure141::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_import_jetty_ex，Invalid parameter";
}

std::string UrmaFailure141::GetId() const
{
    return "urma_141";
}

} // namespace diag
