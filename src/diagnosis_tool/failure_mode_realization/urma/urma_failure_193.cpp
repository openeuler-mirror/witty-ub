#include "urma_failure_193.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure193> g_urma("urma_193");

bool UrmaFailure193::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Invalid parameter, jfc is NULL in jfs_cfg.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure193::GetName() const
{
    return "Jetty对象无效导致创建JFC失败";
}

std::string UrmaFailure193::GetRootCauseDesc() const
{
    return "函数用于创建JFC，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure193::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure193::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure193::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_check_jfc，Invalid parameter, jfc is NULL in "
           "jfs_cfg.。";
}

std::string UrmaFailure193::GetId() const
{
    return "urma_193";
}

} // namespace diag
