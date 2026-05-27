#include "urma_failure_294.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure294> g_urma("urma_294");

bool UrmaFailure294::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_ack_notify' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'delete_jetty_grp failed.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure294::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure294::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure294::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure294::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure294::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_ack_notify，delete_jetty_grp failed.。";
}

std::string UrmaFailure294::GetId() const
{
    return "urma_294";
}

} // namespace diag
