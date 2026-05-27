#include "urma_failure_195.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure195> g_urma("urma_195");

bool UrmaFailure195::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Invalid parameter, jfr is null or jfc is NULL with shared jfr flag.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure195::GetName() const
{
    return "JFR对象无效导致创建JFR失败";
}

std::string UrmaFailure195::GetRootCauseDesc() const
{
    return "函数用于创建JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure195::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure195::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure195::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_jfc，Invalid parameter, jfr is null or jfc is "
           "NULL with shared jfr flag.。";
}

std::string UrmaFailure195::GetId() const
{
    return "urma_195";
}

} // namespace diag
