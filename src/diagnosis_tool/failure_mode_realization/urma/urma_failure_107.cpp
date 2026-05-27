#include "urma_failure_107.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure107> g_urma("urma_107");

bool UrmaFailure107::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_import_health_check_tseg' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Invalid rjetty for health check seg import, health check disabled'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure107::GetName() const
{
    return "Jetty对象、Segment对象无效导致导入健康检查失败";
}

std::string UrmaFailure107::GetRootCauseDesc() const
{
    return "函数用于导入健康检查，调用方传入的Jetty对象、Segment对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure107::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure107::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure107::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_import_health_check_tseg，Invalid rjetty for health check seg "
           "import, health check disabled。";
}

std::string UrmaFailure107::GetId() const
{
    return "urma_107";
}

} // namespace diag
