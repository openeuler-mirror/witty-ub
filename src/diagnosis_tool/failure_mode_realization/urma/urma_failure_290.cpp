#include "urma_failure_290.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure290> g_urma("urma_290");

bool UrmaFailure290::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'create_jetty_grp failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure290::GetName() const
{
    return "Jetty创建时下层资源准备失败";
}

std::string UrmaFailure290::GetRootCauseDesc() const
{
    return "函数负责创建Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure290::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure290::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure290::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_ack_notify，create_jetty_grp failed.";
}

std::string UrmaFailure290::GetId() const
{
    return "urma_290";
}

} // namespace diag
