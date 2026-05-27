#include "urma_failure_191.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure191> g_urma("urma_191");

bool UrmaFailure191::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_create_jetty_check_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, jfc is NULL in jfs_cfg.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure191::GetName() const
{
    return "Jetty对象无效导致创建JFC失败";
}

std::string UrmaFailure191::GetRootCauseDesc() const
{
    return "函数用于创建JFC，调用方传入的Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure191::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure191::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure191::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_create_jetty_check_jfc，Invalid parameter, jfc is NULL in jfs_cfg.";
}

std::string UrmaFailure191::GetId() const
{
    return "urma_191";
}

} // namespace diag
