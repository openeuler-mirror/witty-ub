#include "urma_failure_292.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure292> g_urma("urma_292");

bool UrmaFailure292::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'create_jetty_grp failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure292::GetName() const
{
    return "Jetty创建时下层资源准备失败";
}

std::string UrmaFailure292::GetRootCauseDesc() const
{
    return "函数负责创建Jetty，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure292::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure292::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure292::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_notify，create_jetty_grp failed.。";
}

std::string UrmaFailure292::GetId() const
{
    return "urma_292";
}

} // namespace diag
