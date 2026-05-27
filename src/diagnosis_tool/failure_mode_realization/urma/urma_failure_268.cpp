#include "urma_failure_268.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure268> g_urma("urma_268");

bool UrmaFailure268::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Failed to exec urma_delete_jetty_to_jetty_grp.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure268::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure268::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure268::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure268::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure268::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，Failed to exec urma_delete_jetty_to_jetty_grp.。";
}

std::string UrmaFailure268::GetId() const
{
    return "urma_268";
}

} // namespace diag
