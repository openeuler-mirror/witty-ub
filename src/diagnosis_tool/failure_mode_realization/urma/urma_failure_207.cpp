#include "urma_failure_207.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure207> g_urma("urma_207");

bool UrmaFailure207::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to delete jetty because it has remote jetty, try unbind first'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure207::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure207::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure207::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure207::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure207::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty，Failed to delete jetty because it has remote jetty, try "
           "unbind first";
}

std::string UrmaFailure207::GetId() const
{
    return "urma_207";
}

} // namespace diag
