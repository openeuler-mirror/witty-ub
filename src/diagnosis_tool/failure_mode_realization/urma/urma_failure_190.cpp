#include "urma_failure_190.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure190> g_urma("urma_190");

bool UrmaFailure190::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jetty_to_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'failed to delete jetty to jetty_grp.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure190::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure190::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure190::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure190::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure190::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jetty_to_jetty_grp，failed to delete jetty to jetty_grp.";
}

std::string UrmaFailure190::GetId() const
{
    return "urma_190";
}

} // namespace diag
