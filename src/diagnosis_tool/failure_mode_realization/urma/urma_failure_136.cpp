#include "urma_failure_136.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure136> g_urma("urma_136");

bool UrmaFailure136::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_delete_jetty_batch' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'jetty not from the same dev, cannot delete in a batch, index:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure136::GetName() const
{
    return "Jetty清理阶段下层释放操作失败";
}

std::string UrmaFailure136::GetRootCauseDesc() const
{
    return "函数负责释放或撤销Jetty相关资源，下层provider、驱动或引用状态返回失败，可能残留已创建的URMA资源。";
}

RootCause UrmaFailure136::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure136::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure136::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_delete_jetty_batch，jetty not from the same dev, cannot delete in a "
           "batch, index:";
}

std::string UrmaFailure136::GetId() const
{
    return "urma_136";
}

} // namespace diag
